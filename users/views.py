from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .forms import UserRegisterForm
from django.contrib.auth.decorators import login_required
from .forms import AccountForm, DriverProfileForm, SponsorProfileForm
from .forms import LockedOutAuthenticationForm
from .models import DriverNotification  # NEW import
# Password Change addition
from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy
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