from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import PointChangeAudit
from users.models import DriverProfile, User, SponsorProfile
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

    drivers = User.objects.filter(is_driver=True, is_active=True).order_by("username")
    context = {
        'drivers': drivers
    }
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

    org = _get_sponsor_org(request.user)
    if org is None:
        messages.error(request, "Sponsor organization not set.")
        return redirect("home")

    # filters
    start = parse_date(request.GET.get("start", "") or "")
    end = parse_date(request.GET.get("end", "") or "")
    driver_id = request.GET.get("driver") or ""

    qs = PointChangeAudit.objects.filter(organization=org)

    if start:
        qs = qs.filter(date__date__gte=start)
    if end:
        qs = qs.filter(date__date__lte=end)
    if driver_id:
        qs = qs.filter(driver_id=driver_id)

    qs = qs.select_related("driver", "sponsor").order_by("-date")

    drivers = DriverProfile.objects.filter(organization=org).select_related("user").order_by("user__username")

    ctx = {
        "rows": qs,
        "drivers": drivers,
        "start": start,
        "end": end,
        "driver_id": str(driver_id),
    }
    return render(request, "rewards/reports/points_tracking.html", ctx)


@login_required
def points_tracking_csv(request):
    """CSV export with same filters as HTML report."""
    if not request.user.is_sponsor:
        return HttpResponse("Forbidden", status=403, content_type="text/plain")

    org = _get_sponsor_org(request.user)
    if org is None:
        return HttpResponse("Sponsor organization not set.", status=400, content_type="text/plain")

    start = parse_date(request.GET.get("start", "") or "")
    end = parse_date(request.GET.get("end", "") or "")
    driver_id = request.GET.get("driver") or ""

    qs = PointChangeAudit.objects.filter(organization=org)
    if start:
        qs = qs.filter(date__date__gte=start)
    if end:
        qs = qs.filter(date__date__lte=end)
    if driver_id:
        qs = qs.filter(driver_id=driver_id)

    qs = qs.select_related("driver", "sponsor").order_by("-date")

    # Build CSV
    resp = HttpResponse(content_type="text/csv")
    resp["Content-Disposition"] = 'attachment; filename=\"driver_point_tracking.csv\"'
    w = csv.writer(resp)
    w.writerow(["Driver", "Delta", "Date", "Changed By", "Reason", "New Balance"])

    for r in qs:
        driver_name = getattr(r.driver, "username", "")
        sponsor_name = getattr(r.sponsor, "username", "") if r.sponsor else ""
        w.writerow([driver_name, r.point_change_amt, r.date, sponsor_name, r.reason, r.new_point_balance])

    return resp


def get_driver_points(request, driver_id):
    try:
        driver_profile = DriverProfile.objects.get(user__id=driver_id)
        points = driver_profile.current_points
        return JsonResponse({'status': 'success', 'points': points})
    except DriverProfile.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Driver not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)