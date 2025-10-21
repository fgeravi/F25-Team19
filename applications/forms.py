from django import forms
from applications.models import DriverApplication
from organizations.models import Organization

# --------------------------
# Driver applies to an org
# --------------------------


class ApplicationForm(forms.ModelForm):
    organization = forms.ModelChoiceField(
        queryset=Organization.objects.filter(is_active=True),
        label="Organization",
        empty_label="Select an organization"
    )

    class Meta:
        model = DriverApplication
        fields = ["organization", "message"]
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
