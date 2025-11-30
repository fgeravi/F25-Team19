# users/forms.py

from django import forms
from django import forms
from .models import DriverProfile, DriverSponsor
from organizations.models import Organization
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import User, DriverProfile, SponsorProfile, Organization

class UserRegisterForm(UserCreationForm):
    email = forms.EmailField()
    ACCOUNT_CHOICES = [
        ('driver', 'Driver'),
        ('sponsor', 'Sponsor')
    ]
    account_type = forms.ChoiceField(
        choices=ACCOUNT_CHOICES,
        widget=forms.RadioSelect,
        required=True,
        label="Account Type"
    )
    organization = forms.ModelChoiceField(
        queryset=Organization.objects.all(),
        required=False,  # Only required if user selects sponsor
        label="Organization (sponsors only)"
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'account_type', 'organization', 'password1', 'password2']

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


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Username",
        widget=forms.TextInput(attrs={"autofocus": True, "class": "form-control"})
    )
    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password", "class": "form-control"})
    )
    remember_me = forms.BooleanField(
        required=False,
        initial=False,
        label="Remember me for 2 weeks",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"})
    )

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

    def save(self, commit=True):
        # Save the SponsorProfile first
        instance = super().save(commit=False)

        # Sync the organization name
        if instance.organization:
            instance.organization.name = instance.company_name
            if commit:
                instance.organization.save()

        # Save SponsorProfile
        if commit:
            instance.save()

        return instance



class DriverEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'is_active']
        help_texts = {
            'is_active': 'Uncheck this to deactivate the driver. They will not be able to log in.'
        }

        
class NotificationPreferenceForm(forms.ModelForm):
    class Meta:
        model = DriverProfile
        fields = ["notify_points_change", "notify_order_placed"]
        labels = {
            "notify_points_change": "Email / in-app alerts when my points change",
            "notify_order_placed": "Alerts when I place an order",
        }
        widgets = {
            "notify_points_change": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "notify_order_placed": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

class OrganizationPointValueForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = ["point_value_usd"]
        labels = {
            "point_value_usd": "Dollar value per 1 point",
        }
        help_texts = {
            "point_value_usd": "Example: 0.02 means each point is worth two cents.",
        }
        widgets = {
            "point_value_usd": forms.NumberInput(attrs={
                "step": "0.0001",
                "min": "0.0001",
                "style": "width:8rem;"
            })
        }

class DriverCreationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label="Temporary Password")
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirm Temporary Password")

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')

    def clean_password2(self):
        password = self.cleaned_data.get("password")
        password2 = self.cleaned_data.get("password2")
        if password and password2 and password != password2:
            raise forms.ValidationError("The two temporary passwords do not match.")
        return password2

    def save(self, commit=True, sponsor_profile=None):
        """
        Saves the user and creates a DriverProfile.
        If a 'sponsor_profile' is passed, creates the DriverSponsor relationship.
        """
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        user.is_driver = True
        
        if commit:
            user.save()
            org = sponsor_profile.organization if sponsor_profile else None
            
            driver_profile = DriverProfile.objects.create(
                user=user, 
                organization=org,
                license_number="Pending",
                vehicle_info="Pending"
            )
            if sponsor_profile:
                DriverSponsor.objects.create(
                    driver=driver_profile,
                    sponsor=sponsor_profile,
                    approved=True
                )
                
        return user
    
class SponsorCreationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label="Temporary Password")
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirm Temporary Password")

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')

    def clean_password2(self):
        password = self.cleaned_data.get("password")
        password2 = self.cleaned_data.get("password2")
        if password and password2 and password != password2:
            raise forms.ValidationError("The two temporary passwords do not match.")
        return password2

    def save(self, commit=True, organization=None, company_name="Unknown"):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        user.is_sponsor = True

        if commit:
            user.save()
            if organization:
                SponsorProfile.objects.create(
                    user=user, 
                    organization=organization,
                    company_name=company_name
                )
        return user

    
class DriverImportForm(forms.Form):
    file = forms.FileField(label="Select a pipe-delimited text file (.txt)")

class SponsorPointsPolicyForm(forms.ModelForm):
    class Meta:
        model = SponsorProfile
        fields = ["points_expiration_days"]
        widgets = {
            "points_expiration_days": forms.NumberInput(attrs={"min": 1})
        }
        help_texts = {
            "points_expiration_days": "Set the number of days points remain valid for your drivers."
        }

class AdminBulkImportForm(forms.Form):
    file = forms.FileField(
        label="Select a pipe-delimited text file",
        help_text="Format: Type|Organization|FirstName|LastName|Email"
    )