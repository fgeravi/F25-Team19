# users/forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import User, DriverProfile, SponsorProfile

class UserRegisterForm(UserCreationForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ['username', 'email']

# Lockout logic in authentication forms
class LockedOutAuthenticationForm(AuthenticationForm):
    remember_me = forms.BooleanField(required=False, initial=False)
    
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if (user.is_staff or user.is_superuser) and getattr(user, "lockout_until", None):
            if user.lockout_until > timezone.now():
                when = timezone.localtime(user.lockout_until).strftime('%Y-%m-%d %H:%M:%S')
                raise forms.ValidationError(f"This account is locked until {when}.", code='locked_out')
    
    def get_session_expiry(self):
        """Return session expiry based on remember_me field."""
        from django.conf import settings
        if self.cleaned_data.get('remember_me'):
            # Use extended session length for "remember me"
            return settings.EXTENDED_SESSION_LENGTH
        # Use default session length (will timeout after SESSION_COOKIE_AGE)
        return None

# For admin site login        
class LockedOutAdminAuthenticationForm(AdminAuthenticationForm):
    def _human_until(self, dt):
        """Format a datetime as a friendly local time, cross-platform."""
        local = timezone.localtime(dt)
        try:
            return local.strftime("%-I:%M %p %Z")            
        except ValueError:
            return local.strftime("%I:%M %p %Z").lstrip("0") 

    def clean(self):
        """
        Check lockout *before* attempting authentication so we can show
        a clear error even when the backend blocks the login.
        """
        username = (
            self.data.get("username") or
            self.cleaned_data.get("username") or
            ""  # fallback
        )

        user = None
        if username:
            UserModel = get_user_model()
            try:
                # Handles normalization for the configured USERNAME_FIELD
                user = UserModel._default_manager.get_by_natural_key(username)
            except UserModel.DoesNotExist:
                user = None

        if user:
            lockout_until = getattr(user, "lockout_until", None)
            if lockout_until and lockout_until > timezone.now():
                when = self._human_until(lockout_until)
                remaining = max(1, int((lockout_until - timezone.now()).total_seconds() // 60) + 1)
                raise forms.ValidationError(
                    f"Your account is locked due to too many failed logins. "
                    f"Please try again in about {remaining} minute(s), by {when}.",
                    code="locked_out",
                )

        # Not locked, proceed with normal auth (does the actual authenticate())
        return super().clean()


# account editing forms
class AccountForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["username", "email"]
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
        }

class DriverProfileForm(forms.ModelForm):
    class Meta:
        model = DriverProfile
        fields = ["license_number", "vehicle_info"]
        widgets = {
            "license_number": forms.TextInput(attrs={"class": "form-control"}),
            "vehicle_info": forms.TextInput(attrs={"class": "form-control"}),
        }

class SponsorProfileForm(forms.ModelForm):
    class Meta:
        model = SponsorProfile
        fields = ["company_name"]
        widgets = {
            "company_name": forms.TextInput(attrs={"class": "form-control"}),
        }

