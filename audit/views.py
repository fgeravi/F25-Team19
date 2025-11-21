from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import redirect
from django.contrib import messages
from .models import KnownLoginLocations, LoginAttempt, PasswordChange
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.utils.timezone import make_aware
from datetime import datetime, time
from .forms import ReportFilterForm
from .utils import stream_csv, daterange_filename
from applications.models import DriverApplication
from django.utils.dateparse import parse_date
from itertools import chain
from operator import attrgetter
from rewards.models import PointChangeAudit
from django.http import HttpResponse
from users.models import DriverSponsor

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

    qs = DriverApplication.objects.select_related("organization", "driver").all()

    if request.user.is_staff:
        role = "admin"

    elif getattr(request.user, "is_sponsor", False):
        sponsor_org_id = getattr(
            getattr(request.user, "sponsorprofile", None),
            "organization_id",
            None,
        )
        if sponsor_org_id is None:
            raise PermissionDenied("No organization associated with this sponsor.")
        qs = qs.filter(organization_id=sponsor_org_id)
        role = "sponsor"

    elif getattr(request.user, "is_driver", False):
        qs = qs.filter(driver_id=request.user.id)
        role = "driver"

    else:
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
                a.updated_at.isoformat() if getattr(a, "updated_at", None) else "",
                (a.message or "").replace("\n", " ").strip(),
            ]

    return stream_csv(
        daterange_filename(f"{role}_applications"),
        header,
        rows,
    )


@login_required
def audit_log_report(request):
    """
    Story 315: Audit Log report filterable by event type
    Shows: LoginAttempt, PasswordChange, KnownLoginLocations
    """
    if not (request.user.is_staff or getattr(request.user, "is_sponsor", False)):
        messages.error(request, "Admin or Sponsor access required.")
        return redirect("home")

    # Get filters
    event_type = request.GET.get("event_type", "all")
    start = parse_date(request.GET.get("start", "") or "")
    end = parse_date(request.GET.get("end", "") or "")
    username_filter = request.GET.get("username", "").strip()
    keyword = request.GET.get("keyword", "").strip().lower()

    allowed_usernames = None
    if not request.user.is_staff:
        sponsor_profile = getattr(request.user, 'sponsorprofile', None)
        if sponsor_profile:
            driver_usernames = DriverSponsor.objects.filter(
                sponsor=sponsor_profile,
                approved=True
            ).select_related('driver__user').values_list('driver__user__username', flat=True)
            allowed_usernames = set([request.user.username] + list(driver_usernames))

    events = []

    if event_type in ["all", "login"]:
        login_qs = LoginAttempt.objects.all()
        if start:
            login_qs = login_qs.filter(timestamp__date__gte=start)
        if end:
            login_qs = login_qs.filter(timestamp__date__lte=end)
        if username_filter:
            login_qs = login_qs.filter(username__icontains=username_filter)
        if allowed_usernames is not None:
            login_qs = login_qs.filter(username__in=allowed_usernames)
        
        for item in login_qs:
            events.append({
                'type': 'Login Attempt',
                'user': item.username,
                'timestamp': item.timestamp,
                'ip': item.ip_address or '-',
                'details': 'Success' if item.successful else 'Failed',
                'user_agent': item.user_agent or '-'
            })

    if event_type in ["all", "password"]:
        password_qs = PasswordChange.objects.all()
        if start:
            password_qs = password_qs.filter(timestamp__date__gte=start)
        if end:
            password_qs = password_qs.filter(timestamp__date__lte=end)
        if username_filter:
            password_qs = password_qs.filter(username__icontains=username_filter)
        if allowed_usernames is not None:
            password_qs = password_qs.filter(username__in=allowed_usernames)
        
        for item in password_qs:
            events.append({
                'type': 'Password Change',
                'user': item.username,
                'timestamp': item.timestamp,
                'ip': item.ip_address or '-',
                'details': 'Password changed successfully',
                'user_agent': item.user_agent or '-'
            })

    if event_type in ["all", "location"]:
        location_qs = KnownLoginLocations.objects.select_related('user').all()
        if start:
            location_qs = location_qs.filter(first_seen__date__gte=start)
        if end:
            location_qs = location_qs.filter(first_seen__date__lte=end)
        if username_filter:
            location_qs = location_qs.filter(user__username__icontains=username_filter)
        if allowed_usernames is not None:
            location_qs = location_qs.filter(user__username__in=allowed_usernames)
        
        for item in location_qs:
            location_info = []
            if item.city:
                location_info.append(item.city)
            if item.region:
                location_info.append(item.region)
            if item.country:
                location_info.append(item.country)
            location_str = ', '.join(location_info) if location_info else 'Unknown'
            
            events.append({
                'type': 'New Login Location',
                'user': item.user.username,
                'timestamp': item.first_seen,
                'ip': item.ip_address,
                'details': f"{location_str} ({'Acknowledged' if item.acknowledged else 'Not acknowledged'})",
                'user_agent': '-'
            })

    if event_type in ["all", "points"]:
        points_qs = PointChangeAudit.objects.select_related('driver', 'sponsor').all()
        if start:
            points_qs = points_qs.filter(date__date__gte=start)
        if end:
            points_qs = points_qs.filter(date__date__lte=end)
        if username_filter:
            points_qs = points_qs.filter(driver__username__icontains=username_filter)
        if allowed_usernames is not None:
            points_qs = points_qs.filter(driver__username__in=allowed_usernames)
        
        for item in points_qs:
            sponsor_name = item.sponsor.username if item.sponsor else 'System'
            events.append({
                'type': 'Point Change',
                'user': item.driver.username,
                'timestamp': item.date,
                'ip': '-',
                'details': f"Changed by {sponsor_name}: {'+' if item.point_change_amt > 0 else ''}{item.point_change_amt} points. Reason: {item.reason or 'No reason'}",
                'user_agent': '-'
            })

    # Sort by timestamp descending
    events.sort(key=lambda x: x['timestamp'], reverse=True)

    # Apply keyword filter across all fields
    if keyword:
        filtered_events = []
        for event in events:
            searchable_text = f"{event['type']} {event['user']} {event['ip']} {event['details']} {event['user_agent']}".lower()
            if keyword in searchable_text:
                filtered_events.append(event)
        events = filtered_events

    ctx = {
        'events': events,
        'event_type': event_type,
        'start': start,
        'end': end,
        'username_filter': username_filter,
        'keyword': keyword,
        'is_admin': request.user.is_staff,
    }
    return render(request, "audit/audit_log_report.html", ctx)


@login_required
def audit_log_pdf_export(request):
    """
    Story 310: Export filtered audit log to PDF for sponsors
    Uses browser's print-to-PDF functionality with a print-friendly template
    """
    if not (request.user.is_staff or getattr(request.user, "is_sponsor", False)):
        messages.error(request, "Admin or Sponsor access required.")
        return redirect("home")

    # Get same filters as main report
    event_type = request.GET.get("event_type", "all")
    start = parse_date(request.GET.get("start", "") or "")
    end = parse_date(request.GET.get("end", "") or "")
    username_filter = request.GET.get("username", "").strip()
    keyword = request.GET.get("keyword", "").strip().lower()

    allowed_usernames = None
    if not request.user.is_staff:
        sponsor_profile = getattr(request.user, 'sponsorprofile', None)
        if sponsor_profile:
            driver_usernames = DriverSponsor.objects.filter(
                sponsor=sponsor_profile,
                approved=True
            ).select_related('driver__user').values_list('driver__user__username', flat=True)
            allowed_usernames = set([request.user.username] + list(driver_usernames))

    events = []

    if event_type in ["all", "login"]:
        login_qs = LoginAttempt.objects.all()
        if start:
            login_qs = login_qs.filter(timestamp__date__gte=start)
        if end:
            login_qs = login_qs.filter(timestamp__date__lte=end)
        if username_filter:
            login_qs = login_qs.filter(username__icontains=username_filter)
        if allowed_usernames is not None:
            login_qs = login_qs.filter(username__in=allowed_usernames)
        
        for item in login_qs:
            events.append({
                'type': 'Login Attempt',
                'user': item.username,
                'timestamp': item.timestamp,
                'ip': item.ip_address or '-',
                'details': 'Success' if item.successful else 'Failed',
            })

    if event_type in ["all", "password"]:
        password_qs = PasswordChange.objects.all()
        if start:
            password_qs = password_qs.filter(timestamp__date__gte=start)
        if end:
            password_qs = password_qs.filter(timestamp__date__lte=end)
        if username_filter:
            password_qs = password_qs.filter(username__icontains=username_filter)
        if allowed_usernames is not None:
            password_qs = password_qs.filter(username__in=allowed_usernames)
        
        for item in password_qs:
            events.append({
                'type': 'Password Change',
                'user': item.username,
                'timestamp': item.timestamp,
                'ip': item.ip_address or '-',
                'details': 'Password changed successfully',
            })

    if event_type in ["all", "location"]:
        location_qs = KnownLoginLocations.objects.select_related('user').all()
        if start:
            location_qs = location_qs.filter(first_seen__date__gte=start)
        if end:
            location_qs = location_qs.filter(first_seen__date__lte=end)
        if username_filter:
            location_qs = location_qs.filter(user__username__icontains=username_filter)
        if allowed_usernames is not None:
            location_qs = location_qs.filter(user__username__in=allowed_usernames)
        
        for item in location_qs:
            location_info = []
            if item.city:
                location_info.append(item.city)
            if item.region:
                location_info.append(item.region)
            if item.country:
                location_info.append(item.country)
            location_str = ', '.join(location_info) if location_info else 'Unknown'
            
            events.append({
                'type': 'New Login Location',
                'user': item.user.username,
                'timestamp': item.first_seen,
                'ip': item.ip_address,
                'details': f"{location_str} ({'Acknowledged' if item.acknowledged else 'Not acknowledged'})",
            })

    if event_type in ["all", "points"]:
        points_qs = PointChangeAudit.objects.select_related('driver', 'sponsor').all()
        if start:
            points_qs = points_qs.filter(date__date__gte=start)
        if end:
            points_qs = points_qs.filter(date__date__lte=end)
        if username_filter:
            points_qs = points_qs.filter(driver__username__icontains=username_filter)
        if allowed_usernames is not None:
            points_qs = points_qs.filter(driver__username__in=allowed_usernames)
        
        for item in points_qs:
            sponsor_name = item.sponsor.username if item.sponsor else 'System'
            events.append({
                'type': 'Point Change',
                'user': item.driver.username,
                'timestamp': item.date,
                'ip': '-',
                'details': f"Changed by {sponsor_name}: {'+' if item.point_change_amt > 0 else ''}{item.point_change_amt} points. Reason: {item.reason or 'No reason'}",
            })

    # Sort by timestamp descending
    events.sort(key=lambda x: x['timestamp'], reverse=True)

    # Apply keyword filter
    if keyword:
        filtered_events = []
        for event in events:
            searchable_text = f"{event['type']} {event['user']} {event['ip']} {event['details']}".lower()
            if keyword in searchable_text:
                filtered_events.append(event)
        events = filtered_events

    ctx = {
        'events': events,
        'event_type': event_type,
        'start': start,
        'end': end,
        'username_filter': username_filter,
        'keyword': keyword,
        'generated_by': request.user.username,
        'generated_at': datetime.now(),
    }
    return render(request, "audit/audit_log_pdf.html", ctx)
