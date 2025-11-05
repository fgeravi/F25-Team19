from django import forms
from applications.models import DriverApplication
from organizations.models import Organization
from users.models import SponsorProfile

# --------------------------
# Driver applies to an org
# --------------------------


class ApplicationForm(forms.ModelForm):
    sponsor = forms.ModelChoiceField(
        queryset=SponsorProfile.objects.all(),
        label="Sponsor",
        empty_label="Select a sponsor"
    )

    class Meta:
        model = DriverApplication
        fields = ["sponsor", "message"]
        widgets = {
            "message": forms.Textarea(attrs={"rows": 4}),
        }



# --------------------------
# Sponsor updates application
# --------------------------
class ApplicationUpdateForm(forms.ModelForm):
    class Meta:
        model = DriverApplication
        fields = ["status"]  # sponsor can accept or deny
        widgets = {
            "status": forms.Select(choices=DriverApplication.STATUS_CHOICES),
        }
        labels = {
            "status": "Update Status",
        }
