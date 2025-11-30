from django import forms
from django.contrib.auth import get_user_model
from organizations.models import Organization
from users.models import SponsorProfile, DriverProfile

User = get_user_model()

class DateRangeForm(forms.Form):
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        required=False,
        label="Start Date"
    )
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        required=False,
        label="End Date"
    )

class SponsorPointFilterForm(DateRangeForm):
    driver = forms.ModelChoiceField(
        queryset=User.objects.none(),
        required=False,
        empty_label="All Drivers",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, *args, **kwargs):
        sponsor_user = kwargs.pop('sponsor_user', None)
        super().__init__(*args, **kwargs)
        if sponsor_user and hasattr(sponsor_user, 'sponsorprofile'):
            # FIX: Only fetch drivers directly sponsored by this specific user
            self.fields['driver'].queryset = User.objects.filter(
                driverprofile__sponsorships__sponsor=sponsor_user.sponsorprofile,
                driverprofile__sponsorships__approved=True
            ).distinct()

class SponsorAuditFilterForm(DateRangeForm):
    CAT_CHOICES = [
        ('', 'All Categories'),
        ('profile', 'Profile Changes'),
        ('application', 'Application Decisions'), # Added
        ('point', 'Point Changes'),               # Added
    ]
    category = forms.ChoiceField(
        choices=CAT_CHOICES, 
        required=False, 
        widget=forms.Select(attrs={'class': 'form-select'})
    )

class AdminFilterForm(DateRangeForm):
    sponsor = forms.ModelChoiceField(
        queryset=SponsorProfile.objects.select_related('organization').all(),
        required=False,
        empty_label="All Sponsors",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

class AdminSalesDriverForm(AdminFilterForm):
    driver = forms.ModelChoiceField(
        queryset=User.objects.filter(is_driver=True),
        required=False,
        empty_label="All Drivers",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

class AdminAuditFilterForm(DateRangeForm):
    CAT_CHOICES = [
        ('', 'All Categories'),
        ('login', 'Login Attempts'),
        ('password', 'Password Changes'),
        ('profile', 'Driver Profile Changes'),
        ('application', 'Application Decisions'), # Added
        ('point', 'Point Changes'),               # Added
    ]
    sponsor = forms.ModelChoiceField(
        queryset=SponsorProfile.objects.all(),
        required=False,
        empty_label="All Sponsors",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    category = forms.ChoiceField(
        choices=CAT_CHOICES, 
        required=False, 
        widget=forms.Select(attrs={'class': 'form-select'})
    )