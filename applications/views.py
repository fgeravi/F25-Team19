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
def apply_to_organization(request):
    if not is_driver(request.user):
        messages.error(request, "Only drivers can apply to organizations.")
        return redirect("home")

    if request.method == "POST":
        form = ApplicationForm(request.POST)
        if form.is_valid():
            org = form.cleaned_data["organization"]

            # Check if already applied
            existing = DriverApplication.objects.filter(driver=request.user, organization=org).first()
            if existing:
                messages.info(request, "You have already applied to this organization.")
                return redirect("driver_applications_list")

            # Create application
            DriverApplication.objects.create(
                driver=request.user,
                organization=org,
                message=form.cleaned_data.get("message", "")
            )
            messages.success(request, f"Application sent to {org.name}.")
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

    org = getattr(request.user.sponsorprofile, "organization", None)
    if not org:
        messages.error(request, "You are not associated with an organization.")
        return redirect("home")

    applications = org.applications.all()  # All applications for this sponsor's org
    return render(request, "applications/sponsor_application_list.html", {
        "applications": applications,
        "org": org  # so template can access org.name
    })


# TODO: TEST THIS -> create a new driver, apply to zachtestorg, login as zachsponsor, accept, log in as new driver, view catalogue

# -------------------------
# Sponsor accepts/denies an app
# -------------------------
@login_required
def update_application_status(request, app_id):
    if not is_sponsor(request.user):
        messages.error(request, "Only sponsors can update applications.")
        return redirect("home")

    application = get_object_or_404(DriverApplication, id=app_id)
    org = getattr(request.user.sponsorprofile, "organization", None)

    # Ensure sponsor belongs to the same org
    if application.organization != org:
        messages.error(request, "You cannot update applications for other organizations.")
        return redirect("sponsor_view_applications")  # FIX

    if request.method == "POST":
        form = ApplicationUpdateForm(request.POST, instance=application)
        if form.is_valid():
            form.save()

            # Handle accepted status
            if application.status == "accepted":
                from users.models import DriverProfile

                driver_profile, created = DriverProfile.objects.get_or_create(
                    user=application.driver,
                    defaults={"organization": application.organization}
                )

                if created:
                    messages.success(
                        request,
                        f"DriverProfile created for {application.driver.username} under {application.organization.name}."
                    )
                else:
                    old_org = driver_profile.organization
                    if old_org != application.organization:
                        driver_profile.organization = application.organization
                        driver_profile.save(update_fields=["organization"])
                        old_org_name = old_org.name if old_org else "None"
                        messages.info(
                            request,
                            f"{application.driver.username}'s profile updated from {old_org_name} to {application.organization.name}."
                        )
                    else:
                        messages.info(
                            request,
                            f"{application.driver.username} is already part of {application.organization.name}."
                        )

            messages.success(request, "Application updated.")
            return redirect("sponsor_view_applications")  # FIX
    else:
        form = ApplicationUpdateForm(instance=application)

    return render(request, "applications/update_application.html", {
        "application": application,
        "form": form
    })


# -----------------------------------------
# CSV export
# -----------------------------------------
@login_required
@require_GET
def export_applications_csv(request):
    """
    Staff:    export all applications.
    Sponsors: export applications for their organization.
    Drivers:  export only their own applications.
    """
    user = request.user

    if getattr(user, "is_staff", False):
        role = "staff"
        qs = (
            DriverApplication.objects
            .all()
            .select_related("driver", "organization")
            .order_by("-id")
        )
    elif is_sponsor(user):
        sponsorprofile = getattr(user, "sponsorprofile", None)
        org = getattr(sponsorprofile, "organization", None) if sponsorprofile else None
        if not org:
            return HttpResponseForbidden("Sponsor profile/organization not found.")
        role = "sponsor"
        qs = (
            DriverApplication.objects
            .filter(organization_id=org.id)
            .select_related("driver", "organization")
            .order_by("-id")
        )
    elif is_driver(user):
        role = "driver"
        qs = (
            DriverApplication.objects
            .filter(driver=user)
            .select_related("driver", "organization")
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
        "Organization",
        "Status",
        "Message",
        "Submitted At",
        "Updated At",
    ])

    for app in qs:
        submitted = getattr(app, "created_at", None) or getattr(app, "created", None)
        updated = getattr(app, "updated_at", None) or getattr(app, "modified", None)
        writer.writerow([
            app.pk,
            getattr(app.driver, "username", ""),
            getattr(app.driver, "email", ""),
            getattr(app.organization, "name", ""),
            getattr(app, "status", ""),
            getattr(app, "message", "") or "",
            localtime(submitted).strftime("%Y-%m-%d %H:%M") if submitted else "",
            localtime(updated).strftime("%Y-%m-%d %H:%M") if updated else "",
        ])

    return response
