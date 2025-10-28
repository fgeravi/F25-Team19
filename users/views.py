from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .forms import UserRegisterForm
from django.contrib.auth.decorators import login_required
from .forms import AccountForm, DriverProfileForm, SponsorProfileForm, DriverCreationForm, DriverImportForm
from .forms import LockedOutAuthenticationForm
from .forms import NotificationPreferenceForm
from django.contrib.auth.decorators import login_required
from .models import DriverNotification  # NEW import
# Password Change addition
from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy
from django.utils.crypto import get_random_string
from django.utils import timezone
from audit.models import PasswordChange
from .models import SponsorProfile, DriverProfile, User, DriverChangeAudit, Organization
from .forms import DriverEditForm


@login_required
def home(request):
    organization = None

    # if the user is a driver, get their organization from the driver profile
    if getattr(request.user, "is_driver", False):
        driver_profile = getattr(request.user, "driverprofile", None)
        if driver_profile and driver_profile.organization:
            organization = driver_profile.organization

    # if the user is a sponsor, get their organization from the sponsor profile
    elif getattr(request.user, "is_sponsor", False):
        sponsor_profile = getattr(request.user, "sponsorprofile", None)
        if sponsor_profile and sponsor_profile.organization:
            organization = sponsor_profile.organization

    return render(request, 'users/home.html', {"organization": organization})


def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            
            # Set role based on selection
            account_type = form.cleaned_data['account_type']
            if account_type == 'driver':
                user.is_driver = True
            elif account_type == 'sponsor':
                user.is_sponsor = True

            user.save()  # save the user

            # Optionally, create the profile automatically
            if user.is_driver:
                from .models import DriverProfile
                DriverProfile.objects.create(user=user)
            elif user.is_sponsor:
                from .models import SponsorProfile
                from .models import SponsorProfile
                organization = form.cleaned_data.get('organization')
                if not organization:
                    # fallback: pick first organization or show error
                    organization = Organization.objects.first()
                    SponsorProfile.objects.create(user=user, organization=organization)

            messages.success(request, f'Account created for {user.username}!')
            return redirect('login')
    else:
        form = UserRegisterForm()
    return render(request, 'users/registration/register.html', {'form': form})


# --- Notifications stuff ---

@login_required
def notifications_list(request):
    """List the current user's notifications."""
    notifs = DriverNotification.objects.filter(driver_user=request.user)
    return render(request, 'users/notifications/list.html', {'notifications': notifs})


@login_required
def notification_mark_read(request, pk: int):
    """Mark a single notification as read for the current user."""
    notif = get_object_or_404(DriverNotification, pk=pk, driver_user=request.user)
    if not notif.is_read:
        notif.is_read = True
        notif.save(update_fields=['is_read'])
        messages.success(request, "Notification marked as read.")
    return redirect('notifications_list')

# account management view
@login_required
def account_management(request):
    user = request.user

    user_form = AccountForm(request.POST or None, instance=user)

    driver_form = None
    sponsor_form = None

    if getattr(user, "is_driver", False):
        driver_profile = getattr(user, "driverprofile", None)
        if driver_profile:
            driver_form = DriverProfileForm(request.POST or None, instance=driver_profile)

    if getattr(user, "is_sponsor", False):
        sponsor_profile = getattr(user, "sponsorprofile", None)
        if sponsor_profile:
            sponsor_form = SponsorProfileForm(request.POST or None, instance=sponsor_profile)

    if request.method == "POST":
        forms = [user_form]
        if driver_form: forms.append(driver_form)
        if sponsor_form: forms.append(sponsor_form)

        if all(f.is_valid() for f in forms):
            for f in forms:
                f.save()
            messages.success(request, "Your account has been updated successfully.")
            return redirect("account_management")
        else:
            messages.error(request, "Please correct the errors below.")

    context = {
        "user_form": user_form,
        "driver_form": driver_form,
        "sponsor_form": sponsor_form,
    }
    return render(request, "users/account_management.html", context)

# Password Change Audit
class AuditedPasswordChangeView(PasswordChangeView):
    template_name = 'users/password_change.html'
    success_url = reverse_lazy('password_change_done')

    def form_valid(self, form):
        response = super().form_valid(form)

        # Get request info
        user = self.request.user
        ip = self.request.META.get('REMOTE_ADDR')
        user_agent = self.request.META.get('HTTP_USER_AGENT')

        # Log the event
        PasswordChange.objects.create(
            username=user.username,
            ip_address=ip,
            user_agent=user_agent,
            timestamp=timezone.now()
        )
        return response

@login_required
def manage_drivers_view(request):
    if not request.user.is_sponsor:
        messages.error(request, "You do not have permission to view this page.")
        return redirect('home')

    try:
        sponsor_profile = request.user.sponsorprofile
        organization = sponsor_profile.organization
        
        drivers = User.objects.filter(
            is_driver=True,
            driverprofile__organization=organization
        ).order_by('username')

    except SponsorProfile.DoesNotExist:
        messages.error(request, "Your sponsor profile could not be found.")
        return redirect('home')

    context = {
        'drivers': drivers
    }
    return render(request, 'users/manage_drivers.html', context)

@login_required
def edit_point_value_view(request):
    """
    Sponsor can change how much 1 point is worth in dollars
    for THEIR organization only.
    """
    # Must be a sponsor
    if not getattr(request.user, "is_sponsor", False):
        messages.error(request, "You do not have permission to edit point settings.")
        return redirect("home")

    # Get sponsor's org
    sponsor_profile = getattr(request.user, "sponsorprofile", None)
    if not sponsor_profile or not sponsor_profile.organization:
        messages.error(request, "You are not assigned to an organization.")
        return redirect("home")

    org = sponsor_profile.organization

    from .forms import OrganizationPointValueForm
    if request.method == "POST":
        form = OrganizationPointValueForm(request.POST, instance=org)
        if form.is_valid():
            form.save()
            messages.success(request, "Point value updated for your organization.")
            return redirect("edit_point_value")
    else:
        form = OrganizationPointValueForm(instance=org)

    return render(request, "users/sponsor/edit_point_value.html", {
        "form": form,
        "org": org,
    })


@login_required
def edit_driver_view(request, driver_id):
    if not request.user.is_sponsor:
        messages.error(request, "You do not have permission to perform this action.")
        return redirect('home')

    driver_user = get_object_or_404(User, id=driver_id, is_driver=True)

    if request.method == 'POST':
        form = DriverEditForm(request.POST, instance=driver_user)
        if form.is_valid():
            # Story 461: Log changes before saving
            for field in form.changed_data:
                DriverChangeAudit.objects.create(
                    sponsor=request.user,
                    driver=driver_user,
                    field_name=field,
                    old_value=form.initial.get(field),
                    new_value=form.cleaned_data.get(field)
                )
            
            form.save()
            messages.success(request, f"Successfully updated profile for {driver_user.username}.")
            return redirect('manage_drivers')
    else:
        form = DriverEditForm(instance=driver_user)

    context = {
        'form': form,
        'driver_user': driver_user
    }
    return render(request, 'users/edit_driver.html', context)

@login_required
def notification_preferences(request):
    # Only drivers have these prefs right now
    if not getattr(request.user, "is_driver", False):
        messages.error(request, "Only drivers can manage notification preferences.")
        return redirect("home")

    driver_profile = getattr(request.user, "driverprofile", None)
    if not driver_profile:
        messages.error(request, "Driver profile not found.")
        return redirect("home")

    if request.method == "POST":
        form = NotificationPreferenceForm(request.POST, instance=driver_profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Your notification settings have been updated.")
            return redirect("notification_preferences")
    else:
        form = NotificationPreferenceForm(instance=driver_profile)

    return render(
        request,
        "users/notifications/preferences.html",
        {
            "form": form,
        },
    )

@login_required
def add_driver_view(request):
    if not request.user.is_sponsor:
        messages.error(request, "You do not have permission to perform this action.")
        return redirect('home')

    try:
        sponsor_organization = request.user.sponsorprofile.organization
    except SponsorProfile.DoesNotExist:
        messages.error(request, "Your sponsor profile could not be found.")
        return redirect('home')

    if request.method == 'POST':
        form = DriverCreationForm(request.POST)
        if form.is_valid():
            form.save(organization=sponsor_organization)
            messages.success(request, "New driver has been added successfully.")
            return redirect('manage_drivers')
    else:
        form = DriverCreationForm()

    context = {
        'form': form
    }
    return render(request, 'users/add_driver.html', context)




@login_required
def import_drivers_view(request):
    if not request.user.is_sponsor:
        messages.error(request, "You do not have permission to perform this action.")
        return redirect('home')

    try:
        sponsor_organization = request.user.sponsorprofile.organization
    except SponsorProfile.DoesNotExist:
        messages.error(request, "Your sponsor profile could not be found.")
        return redirect('home')

    error_messages = []
    success_messages = []

    if request.method == 'POST':
        form = DriverImportForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = request.FILES['file']
            
            try:
                lines = uploaded_file.read().decode('utf-8').splitlines()

                for i, line in enumerate(lines):
                    line_num = i + 1
                    try:
                        parts = line.strip().split('|')

                        if len(parts) != 4:
                            error_messages.append(f"Line {line_num}: Invalid format. Must be 4 values per line.")
                            continue
                        
                        user_type, first_name, last_name, email = parts

                        if user_type not in ['D', 'S']:
                            error_messages.append(f"Line {line_num}: Invalid user type '{user_type}'.")
                            continue
                        if not all([first_name, last_name, email]):
                            error_messages.append(f"Line {line_num}: First name, last name, and email are required.")
                            continue
                        if User.objects.filter(email=email).exists():
                            error_messages.append(f"Line {line_num}: User with email '{email}' already exists.")
                            continue

                        temp_password = get_random_string(10)
               
                        user = User.objects.create_user(
                            username=email,
                            email=email,
                            first_name=first_name,
                            last_name=last_name,
                            password=temp_password
                        )

                        if user_type == 'D':
                            user.is_driver = True
                            DriverProfile.objects.create(user=user, organization=sponsor_organization)
                        elif user_type == 'S':
                            user.is_sponsor = True
                            SponsorProfile.objects.create(user=user, organization=sponsor_organization)
                        
                        user.save()
                        
                        success_messages.append(f"Successfully created user for {email}. Temporary password: {temp_password}")

                    except Exception as e:
                        error_messages.append(f"Line {line_num}: An unexpected error occurred - {e}")
            
            except Exception as e:
                messages.error(request, f"Could not read the uploaded file. Error: {e}")

    else:
        form = DriverImportForm()

    context = {
        'form': form,
        'error_messages': error_messages,
        'success_messages': success_messages,
    }
    return render(request, 'users/import_drivers.html', context)