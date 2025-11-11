from django import forms
from .models import IssueReport

class IssueReportForm(forms.ModelForm):
    class Meta:
        model = IssueReport
        fields = ['subject', 'description', 'urgency']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
        }