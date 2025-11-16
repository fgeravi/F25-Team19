from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, HttpResponseForbidden
from django.utils.timezone import localtime
from django.views.decorators.http import require_GET 
import csv

from .models import DriverApplication
from .forms import ApplicationForm, ApplicationUpdateForm
from users.models import is_driver, is_sponsor

# ---------------------------
# Driver list of applications
# ---------------------------
@login_required
def driver_applications_list(request):
    if not is_driver(request.user):
        messages.error(request, "Only drivers can view their applications.")
        return redirect("home")

    applications = DriverApplication.objects.filter(driver=request.user)
    return render(
        request,
        "applications/driver_application_list.html",
        {"applications": applications}
    )


# -------------------------
# Driver applies to an org
# -------------------------
@login_required
def apply_to_sponsor(request):
    if not is_driver(request.user):
        messages.error(request, "Only drivers can apply to sponsors.")
        return redirect("home")

    if request.method == "POST":
        form = ApplicationForm(request.POST)
        if form.is_valid():
            sponsor = form.cleaned_data["sponsor"]

            # Check if already applied
            existing = DriverApplication.objects.filter(driver=request.user, sponsor=sponsor).first()
            if existing:
                messages.info(request, "You have already applied to this sponsor.")
                return redirect("driver_applications_list")

            # Create application
            DriverApplication.objects.create(
                driver=request.user,
                sponsor=sponsor,
                message=form.cleaned_data.get("message", "")
            )
            messages.success(request, f"Application sent to {sponsor.user.username}.")
            return redirect("driver_applications_list")
    else:
        form = ApplicationForm()

    return render(request, "applications/apply.html", {"form": form})


# -------------------------
# Sponsor views applications
# -------------------------
@login_required
def sponsor_view_applications(request):
    if not is_sponsor(request.user):
        messages.error(request, "Only sponsors can view applications.")
        return redirect("home")

    sponsor = getattr(request.user, "sponsorprofile", None)
    if not sponsor:
        messages.error(request, "Sponsor profile not found.")
        return redirect("home")

    applications = sponsor.applications.all()  # Applications directly for this sponsor
    return render(request, "applications/sponsor_application_list.html", {
        "applications": applications,
        "sponsor": sponsor  # template can access sponsor.user.username or sponsor.organization.name
    })


# -------------------------
# Sponsor accepts/denies an app
# -------------------------
@login_required
def update_application_status(request, app_id):
    if not is_sponsor(request.user):
        messages.error(request, "Only sponsors can update applications.")
        return redirect("home")

    application = get_object_or_404(DriverApplication, id=app_id)
    sponsor_profile = getattr(request.user, "sponsorprofile", None)

    if not sponsor_profile:
        messages.error(request, "You do not have a sponsor profile.")
        return redirect("home")

    if application.sponsor != sponsor_profile:
        messages.error(request, "You cannot update applications for other sponsors.")
        return redirect("sponsor_applications")

    # Record the old status BEFORE updating
    previous_status = application.status

    if request.method == "POST":
        form = ApplicationUpdateForm(request.POST, instance=application)

        if form.is_valid():
            application = form.save(commit=False)
            new_status = application.status

            # ---- ACCEPT LOGIC ----
            if new_status == "accepted":
                handle_accept(application, sponsor_profile)

            # ---- DENY / UNACCEPT LOGIC ----
            elif previous_status == "accepted" and new_status != "accepted":
                handle_unaccept(application, sponsor_profile)

            application.save()
            messages.success(request, "Application updated.")
            return redirect("sponsor_applications")

    else:
        form = ApplicationUpdateForm(instance=application)

    return render(request, "applications/update_application.html", {
        "application": application,
        "form": form
    })


# ======================================================
# Helper: Accept a driver
# ======================================================
def handle_accept(application, sponsor_profile):
    from users.models import DriverProfile, DriverSponsor

    driver = application.driver

    # Create or fetch profile
    driver_profile, created = DriverProfile.objects.get_or_create(
        user=driver,
        defaults={"organization": sponsor_profile.organization}
    )

    # If profile existed but org changed → update org
    if not created and driver_profile.organization != sponsor_profile.organization:
        driver_profile.organization = sponsor_profile.organization
        driver_profile.save(update_fields=["organization"])

    # Ensure DriverSponsor relationship exists
    DriverSponsor.objects.get_or_create(
        driver=driver_profile,
        sponsor=sponsor_profile
    )

    return driver_profile


# ======================================================
# Helper: Undo acceptance (only when denying after accepted)
# ======================================================
def handle_unaccept(application, sponsor_profile):
    from users.models import DriverProfile, DriverSponsor

    driver = application.driver

    driver_profile = DriverProfile.objects.filter(user=driver).first()
    if not driver_profile:
        return

    # Remove org only if this sponsor was the one that accepted them
    if driver_profile.organization == sponsor_profile.organization:
        driver_profile.organization = None
        driver_profile.save(update_fields=["organization"])

    # Remove relationship
    DriverSponsor.objects.filter(
        driver=driver_profile,
        sponsor=sponsor_profile
    ).delete()




# -----------------------------------------
# CSV export
# -----------------------------------------
@login_required
@require_GET
@login_required
@require_GET
def export_applications_csv(request):
    """
    CSV export of driver applications.

    Staff:    export all applications.
    Sponsors: export applications for their sponsor profile.
    Drivers:  export only their own applications.
    """
    user = request.user

    if getattr(user, "is_staff", False):
        role = "staff"
        qs = (
            DriverApplication.objects
            .all()
            .select_related("driver", "sponsor__organization")
            .order_by("-id")
        )
    elif is_sponsor(user):
        sponsorprofile = getattr(user, "sponsorprofile", None)
        if not sponsorprofile:
            return HttpResponseForbidden("Sponsor profile not found.")
        role = "sponsor"
        qs = (
            DriverApplication.objects
            .filter(sponsor_id=sponsorprofile.id)
            .select_related("driver", "sponsor__organization")
            .order_by("-id")
        )
    elif is_driver(user):
        role = "driver"
        qs = (
            DriverApplication.objects
            .filter(driver=user)
            .select_related("driver", "sponsor__organization")
            .order_by("-id")
        )
    else:
        return HttpResponseForbidden("Not authorized (no role).")

    filename = f"driver_applications_{role}.csv"
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response["X-Export-Role"] = role
    response["X-Export-Count"] = str(qs.count())

    writer = csv.writer(response)
    writer.writerow([
        "Application ID",
        "Driver Username",
        "Driver Email",
        "Sponsor",
        "Sponsor Organization",
        "Status",
        "Message",
        "Submitted At",
        "Updated At",
    ])

    for app in qs:
        submitted = getattr(app, "created_at", None)
        updated = getattr(app, "updated_at", None)
        writer.writerow([
            app.pk,
            getattr(app.driver, "username", ""),
            getattr(app.driver, "email", ""),
            getattr(app.sponsor.user, "username", ""),
            getattr(app.sponsor.organization, "name", ""),
            getattr(app, "status", ""),
            getattr(app, "message", "") or "",
            localtime(submitted).strftime("%Y-%m-%d %H:%M") if submitted else "",
            localtime(updated).strftime("%Y-%m-%d %H:%M") if updated else "",
        ])

    return response
