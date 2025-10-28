from django import forms

class ReportFilterForm(forms.Form):
    start = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    end = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    status = forms.ChoiceField(
        required=False,
        choices=[("", "All"), ("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected")],
    )
