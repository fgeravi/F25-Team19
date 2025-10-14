from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .forms import UserRegisterForm
from django.contrib.auth.decorators import login_required
from .forms import AccountForm, DriverProfileForm, SponsorProfileForm
from .forms import LockedOutAuthenticationForm
from .models import DriverNotification  # NEW import


@login_required
def home(request):
    return render(request, 'home.html')


def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}!')
            return redirect('login')
    else:
        form = UserRegisterForm()
    return render(request, 'registration/register.html', {'form': form})


# --- Notifications stuff ---

@login_required
def notifications_list(request):
    """List the current user's notifications."""
    notifs = DriverNotification.objects.filter(driver_user=request.user)
    return render(request, 'notifications/list.html', {'notifications': notifs})


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


