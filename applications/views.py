from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import DriverApplication
from .forms import ApplicationForm, ApplicationUpdateForm
from users.models import is_driver, is_sponsor

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
                return redirect("home")

            # Create application
            DriverApplication.objects.create(
                driver=request.user,
                organization=org,
                message=form.cleaned_data.get("message", "")
            )
            messages.success(request, f"Application sent to {org.name}.")
            return redirect("home")
    else:
        form = ApplicationForm()

    return render(request, "applications/apply_to_organization.html", {"form": form})


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
    return render(request, "applications/application_list.html", {
        "applications": applications,
        "org": org  # <-- pass org so template can access org.name
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
    org = getattr(request.user.sponsorprofile, "organization", None)

    # Make sure sponsor belongs to the same org
    if application.organization != org:
        messages.error(request, "You cannot update applications for other organizations.")
        return redirect("sponsor_applications")

    if request.method == "POST":
        form = ApplicationUpdateForm(request.POST, instance=application)
        if form.is_valid():
            form.save()
            messages.success(request, f"Application updated.")
            return redirect("sponsor_applications")
    else:
        form = ApplicationUpdateForm(instance=application)

    return render(request, "applications/update_application.html", {
        "application": application,
        "form": form
    })
