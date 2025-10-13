# users/forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.utils import timezone
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.admin.forms import AdminAuthenticationForm
# Import your custom User model
from .models import User  # Or from users.models import User

class UserRegisterForm(UserCreationForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ['username', 'email']

# Lockout logic in authentication forms
class LockedOutAuthenticationForm(AuthenticationForm):
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if (user.is_staff or user.is_superuser) and getattr(user, "lockout_until", None):
            if user.lockout_until > timezone.now():
                when = timezone.localtime(user.lockout_until).strftime('%Y-%m-%d %H:%M:%S')
                raise forms.ValidationError(f"This account is locked until {when}.", code='locked_out')

# For admin site login        
class LockedOutAdminAuthenticationForm(AdminAuthenticationForm):
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if (user.is_staff or user.is_superuser) and getattr(user, "lockout_until", None):
            if user.lockout_until > timezone.now():
                when = timezone.localtime(user.lockout_until).strftime('%Y-%m-%d %H:%M:%S')
                raise forms.ValidationError(f"This account is locked until {when}.", code='locked_out')