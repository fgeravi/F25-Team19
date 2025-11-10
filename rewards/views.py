from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import PointChangeAudit
from users.models import DriverProfile, User, SponsorProfile, DriverSponsor
from django.shortcuts import redirect
from django.contrib import messages
from .models import award_points_to_driver
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum
import csv
from django.http import HttpResponse, JsonResponse
from django.utils.dateparse import parse_date


@login_required
def point_dashboard(request):
    if not request.user.is_driver:
        return redirect('home')

    search_query = request.GET.get('q', '')
    sort_order = request.GET.get('sort', '-date')

    valid_sort_orders = ['date', '-date', 'point_change_amt', '-point_change_amt']
    if sort_order not in valid_sort_orders:
        sort_order = '-date'
    try:
        driver_profile = request.user.driverprofile
        current_balance = driver_profile.current_points

        transactions = PointChangeAudit.objects.filter(driver=request.user)

        if search_query:
            transactions = transactions.filter(reason__icontains=search_query)

        transactions = transactions.order_by(sort_order)

        seven_days_ago = timezone.now() - timedelta(days=7)
        weekly_earnings = PointChangeAudit.objects.filter(
            driver=request.user,
            date__gte=seven_days_ago,
            point_change_amt__gt=0
        ).aggregate(total=Sum('point_change_amt'))['total'] or 0

    except DriverProfile.DoesNotExist:
        current_balance = 0
        transactions = []
        weekly_earnings = 0

    context = {
        'current_balance': current_balance,
        'transactions': transactions,
        'weekly_earnings': weekly_earnings,
        'search_query': search_query,
        'sort_order': sort_order,
    }
    return render(request, 'rewards/dashboard.html', context)


@login_required
def add_points_view(request):
    if not request.user.is_sponsor:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('home')

    sponsor_profile = getattr(request.user, "sponsorprofile", None)
    if not sponsor_profile:
        messages.error(request, "Your sponsor profile could not be found.")
        return redirect("home")

    if request.method == 'POST':
        try:
            driver_id = request.POST.get('driver')
            points = int(request.POST.get('points'))
            reason = (request.POST.get('reason') or "").strip()

            # --- Story 480: reason is required ---
            if not reason:
                messages.error(request, "Reason is required when adding or deducting points.")
                return redirect('rewards:add_points')

            sponsor_user = request.user
            driver_user = User.objects.get(pk=driver_id, is_driver=True)

            # NEW: ensure this driver is actually linked to this sponsor
            if not DriverSponsor.objects.filter(
                sponsor=sponsor_profile,
                driver__user=driver_user,
                approved=True
            ).exists():
                messages.error(request, "That driver is not linked to you.")
                return redirect('rewards:add_points')

            success, message = award_points_to_driver(
                sponsor_user=sponsor_user,
                driver_user=driver_user,
                points=points,
                reason=reason
            )

            if success:
                messages.success(request, message)
            else:
                messages.error(request, message)

        except User.DoesNotExist:
            messages.error(request, "The selected driver does not exist.")
        except ValueError:
            messages.error(request, "Please enter a valid number for points.")
        except Exception as e:
            messages.error(request, f"An error occurred: {e}")

        return redirect('rewards:add_points')

    # NEW: driver list limited to this sponsor’s linked/approved drivers
    drivers = (
        User.objects
        .filter(
            is_driver=True,
            is_active=True,
            driverprofile__sponsorships__sponsor=sponsor_profile,
            driverprofile__sponsorships__approved=True,
        )
        .order_by("username")
        .distinct()
    )

    context = {"drivers": drivers}
    return render(request, 'rewards/add_points.html', context)


# Sponsor Driver Point Tracking (HTML + CSV)

def _get_sponsor_org(user):
    """Return the sponsor's organization or None."""
    try:
        sp = SponsorProfile.objects.get(user=user)
        return sp.organization
    except SponsorProfile.DoesNotExist:
        return None


@login_required
def points_tracking_report(request):
    """
    Sponsor-scoped HTML report.
    Filters:
      - start, end (YYYY-MM-DD)
      - driver (optional user id)
    Shows: driver, delta, date, changed_by, reason
    """
    if not request.user.is_sponsor:
        messages.error(request, "Sponsor access required.")
        return redirect("home")

    # NEW: scope by sponsor↔driver relation instead of org
    sponsor_profile = getattr(request.user, "sponsorprofile", None)
    if not sponsor_profile:
        messages.error(request, "Sponsor profile not found.")
        return redirect("home")

    # filters
    start = parse_date(request.GET.get("start", "") or "")
    end = parse_date(request.GET.get("end", "") or "")
    driver_id = request.GET.get("driver") or ""
    sort_order = request.GET.get("sort", "desc")

    # NEW: audits only for drivers linked to this sponsor
    linked_driver_users = (
        User.objects
        .filter(
            is_driver=True,
            driverprofile__sponsorships__sponsor=sponsor_profile,
            driverprofile__sponsorships__approved=True,
        )
        .distinct()
    )

    qs = PointChangeAudit.objects.filter(driver__in=linked_driver_users)

    if start:
        qs = qs.filter(date__date__gte=start)
    if end:
        qs = qs.filter(date__date__lte=end)
    if driver_id:
        qs = qs.filter(driver_id=driver_id)

    # Apply sorting
    if sort_order == "asc":
        qs = qs.select_related("driver", "sponsor").order_by("date")
    else:  # default to desc
        qs = qs.select_related("driver", "sponsor").order_by("-date")

    # NEW: driver dropdown = only linked drivers (use DriverProfile for template compatibility)
    drivers = (
        DriverProfile.objects
        .filter(
            sponsorships__sponsor=sponsor_profile,
            sponsorships__approved=True,
        )
        .select_related("user")
        .order_by("user__username")
        .distinct()
    )

    ctx = {
        "rows": qs,
        "drivers": drivers,
        "start": start,
        "end": end,
        "driver_id": str(driver_id),
        "sort_order": sort_order,
    }
    return render(request, "rewards/reports/points_tracking.html", ctx)


@login_required
def points_tracking_csv(request):
    """CSV export with same filters as HTML report."""
    if not request.user.is_sponsor:
        return HttpResponse("Forbidden", status=403, content_type="text/plain")

    # NEW: scope by sponsor↔driver relation instead of org
    sponsor_profile = getattr(request.user, "sponsorprofile", None)
    if not sponsor_profile:
        return HttpResponse("Sponsor profile not found.", status=400, content_type="text/plain")

    start = parse_date(request.GET.get("start", "") or "")
    end = parse_date(request.GET.get("end", "") or "")
    driver_id = request.GET.get("driver") or ""
    sort_order = request.GET.get("sort", "desc")

    linked_driver_users = (
        User.objects
        .filter(
            is_driver=True,
            driverprofile__sponsorships__sponsor=sponsor_profile,
            driverprofile__sponsorships__approved=True,
        )
        .distinct()
    )

    qs = PointChangeAudit.objects.filter(driver__in=linked_driver_users)
    if start:
        qs = qs.filter(date__date__gte=start)
    if end:
        qs = qs.filter(date__date__lte=end)
    if driver_id:
        qs = qs.filter(driver_id=driver_id)

    # Apply sorting
    if sort_order == "asc":
        qs = qs.select_related("driver", "sponsor").order_by("date")
    else:  # default to desc
        qs = qs.select_related("driver", "sponsor").order_by("-date")

    # Build CSV
    resp = HttpResponse(content_type="text/csv")
    resp["Content-Disposition"] = 'attachment; filename="driver_point_tracking.csv"'
    w = csv.writer(resp)
    w.writerow(["Driver", "Delta", "Date", "Changed By", "Reason", "New Balance"])

    for r in qs:
        driver_name = getattr(r.driver, "username", "")
        sponsor_name = getattr(r.sponsor, "username", "") if r.sponsor else ""
        w.writerow([driver_name, r.point_change_amt, r.date, sponsor_name, r.reason, r.new_point_balance])

    return resp


def get_driver_points(request, driver_id):
    # NEW: return sponsor-specific points via DriverSponsor (not global DriverProfile.current_points)
    if not getattr(request.user, "is_sponsor", False):
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)

    sponsor_profile = getattr(request.user, "sponsorprofile", None)
    if not sponsor_profile:
        return JsonResponse({'status': 'error', 'message': 'Sponsor profile not found'}, status=404)

    try:
        ds = DriverSponsor.objects.get(
            sponsor=sponsor_profile,
            driver__user__id=driver_id,
            approved=True
        )
        return JsonResponse({'status': 'success', 'points': ds.points})
    except DriverSponsor.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Driver not linked to you'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)