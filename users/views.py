from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .forms import UserRegisterForm
from django.contrib.auth.decorators import login_required

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