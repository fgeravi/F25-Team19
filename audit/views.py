from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import redirect
from django.contrib import messages
from .models import KnownLoginLocations
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.utils.timezone import make_aware
from datetime import datetime, time
from .forms import ReportFilterForm
from .utils import stream_csv, daterange_filename
from applications.models import DriverApplication

# Create your views here.

def ack_all_locations(request):    
    KnownLoginLocations.objects.filter(user=request.user, acknowledged=False).update(acknowledged=True)
    messages.success(request, "Notification dismissed.")
    return redirect('/admin/')

def _apply_filters(qs, form):
    if not form.is_valid():
        return qs
    start = form.cleaned_data.get("start")
    end = form.cleaned_data.get("end")
    status = form.cleaned_data.get("status")
    if start:
        qs = qs.filter(created_at__gte=make_aware(datetime.combine(start, time.min)))
    if end:
        qs = qs.filter(created_at__lte=make_aware(datetime.combine(end, time.max)))
    if status:
        qs = qs.filter(status=status)  
    return qs

@login_required
def report_csv(request):
    form = ReportFilterForm(request.GET or None)

    qs = DriverApplication.objects.all().select_related("organization", "driver")

    if request.user.has_perm("audit.can_download_reports"):
        sponsor_org_id = getattr(getattr(request.user, "sponsorprofile", None), "organization_id", None)
        if sponsor_org_id:
            qs = qs.filter(organization_id=sponsor_org_id)
        role = "sponsor"

    elif request.user.has_perm("audit.can_download_own_reports"):
        qs = qs.filter(driver_id=request.user.id)
        role = "driver"

    else:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("You do not have access to download reports.")

    qs = _apply_filters(qs, form)

    header = ["ID", "Driver", "Organization", "Status", "Created At", "Updated At", "Message"]

    def rows():
        for a in qs.iterator(chunk_size=1000):
            yield [
                a.id,
                getattr(a.driver, "username", getattr(a.driver, "email", "")),
                getattr(a.organization, "name", ""),
                a.status,
                a.created_at.isoformat() if a.created_at else "",
                a.updated_at.isoformat() if a.updated_at else "",
                (a.message or "").replace("\n", " ").strip(),
            ]

    return stream_csv(daterange_filename(f"{role}_applications"), header, rows)