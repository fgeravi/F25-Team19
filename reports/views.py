import csv
from datetime import datetime
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum, F, Q
from django.utils import timezone

from users.models import User, DriverChangeAudit
from organizations.models import Organization
from rewards.models import PointChangeAudit
from catalogue.models import Order, OrderItem
from applications.models import DriverApplication
from audit.models import LoginAttempt, PasswordChange
from .forms import (
    SponsorPointFilterForm, SponsorAuditFilterForm, 
    AdminFilterForm, AdminSalesDriverForm, AdminAuditFilterForm
)

# --- Helper Functions ---

def is_admin(user):
    return user.is_superuser or user.is_staff

def is_sponsor(user):
    return getattr(user, 'is_sponsor', False)

def get_my_drivers(user):
    if not hasattr(user, 'sponsorprofile'):
        return User.objects.none()
    return User.objects.filter(
        driverprofile__sponsorships__sponsor=user.sponsorprofile,
        driverprofile__sponsorships__approved=True
    )

def export_csv(filename, headers, rows):
    """Generic CSV generator"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
    writer = csv.writer(response)
    writer.writerow(headers)
    for row in rows:
        clean_row = [
            x.strftime('%Y-%m-%d %H:%M') if hasattr(x, 'strftime') else x 
            for x in row
        ]
        writer.writerow(clean_row)
    return response

def get_date_range(data):
    """Extract start/end dates from form data"""
    start = data.get('start_date')
    end = data.get('end_date')
    
    if not start:
        start = datetime(2000, 1, 1).date()
    if not end:
        end = timezone.now().date()
        
    return start, end

# --- Main Index ---

@login_required
def reports_index(request):
    return render(request, 'reports/index.html')

# --- SPONSOR REPORTS ---

@login_required
@user_passes_test(is_sponsor)
def sponsor_point_tracking(request):
    form = SponsorPointFilterForm(request.GET, sponsor_user=request.user)
    my_drivers = get_my_drivers(request.user)
    
    logs = PointChangeAudit.objects.none()
    if hasattr(request.user, 'sponsorprofile'):
        org = request.user.sponsorprofile.organization
        logs = PointChangeAudit.objects.filter(
            organization=org,
            driver__in=my_drivers
        ).select_related('driver', 'sponsor')

    if form.is_valid():
        start, end = get_date_range(form.cleaned_data)
        logs = logs.filter(date__date__range=(start, end))
        
        if form.cleaned_data.get('driver'):
            selected_driver = form.cleaned_data['driver']
            if selected_driver in my_drivers:
                logs = logs.filter(driver=selected_driver)

    if 'download_csv' in request.GET:
        headers = ['Driver', 'Point Change', 'Reason', 'Date', 'Sponsor Admin', 'New Balance']
        rows = []
        for log in logs:
            rows.append([
                log.driver.username,
                log.point_change_amt,
                log.reason,
                log.date,
                log.sponsor.username if log.sponsor else "System",
                log.new_point_balance
            ])
        return export_csv(f"point_report_{timezone.now().date()}", headers, rows)

    return render(request, 'reports/sponsor_points.html', {'form': form, 'logs': logs})

@login_required
@user_passes_test(is_sponsor)
def sponsor_audit_log(request):
    form = SponsorAuditFilterForm(request.GET)
    combined_logs = []
    
    start = datetime(2000, 1, 1).date()
    end = timezone.now().date()
    cat = ''

    if form.is_valid():
        start, end = get_date_range(form.cleaned_data)
        cat = form.cleaned_data.get('category')

    my_drivers = get_my_drivers(request.user)

    if not cat or cat == 'profile':
        profile_changes = DriverChangeAudit.objects.filter(
            driver__in=my_drivers, 
            date__date__range=(start, end)
        ).select_related('driver')
        
        for item in profile_changes:
            combined_logs.append({
                'date': item.date,
                'type': 'Profile Edit',
                'driver': item.driver.username,
                'details': f"Changed '{item.field_name}': {item.old_value} -> {item.new_value}",
                'reason': item.reason
            })

    if not cat or cat == 'application':
        if hasattr(request.user, 'sponsorprofile'):
            apps = DriverApplication.objects.filter(
                sponsor=request.user.sponsorprofile,
                updated_at__date__range=(start, end)
            ).exclude(status='pending').select_related('driver')

            for app in apps:
                combined_logs.append({
                    'date': app.updated_at,
                    'type': 'Application Decision',
                    'driver': app.driver.username,
                    'details': f"Status set to: {app.get_status_display().upper()}",
                    'reason': app.message or "No reason provided"
                })
    if not cat or cat == 'point':
        if hasattr(request.user, 'sponsorprofile'):
            org = request.user.sponsorprofile.organization
            point_changes = PointChangeAudit.objects.filter(
                organization=org,
                driver__in=my_drivers,
                date__date__range=(start, end)
            ).select_related('driver')

            for pt in point_changes:
                combined_logs.append({
                    'date': pt.date,
                    'type': 'Point Change',
                    'driver': pt.driver.username,
                    'details': f"Awarded {pt.point_change_amt} points",
                    'reason': pt.reason
                })
    combined_logs.sort(key=lambda x: x['date'], reverse=True)

    if 'download_csv' in request.GET:
        headers = ['Date', 'Type', 'Driver', 'Details', 'Reason']
        rows = [[l['date'], l['type'], l['driver'], l['details'], l['reason']] for l in combined_logs]
        return export_csv("sponsor_audit_log", headers, rows)

    return render(request, 'reports/sponsor_audit.html', {'form': form, 'logs': combined_logs})

# --- ADMIN REPORTS ---

@login_required
@user_passes_test(is_admin)
def admin_sales_by_sponsor(request):
    form = AdminFilterForm(request.GET)
    orders = Order.objects.exclude(status='CANCELLED').select_related('organization', 'driver')
    
    if form.is_valid():
        start, end = get_date_range(form.cleaned_data)
        orders = orders.filter(created_at__date__range=(start, end))
        
        sponsor_profile = form.cleaned_data.get('sponsor')
        if sponsor_profile:
            orders = orders.filter(organization=sponsor_profile.organization)

    report_data = []
    total_sales_points = 0
    
    for order in orders:
        points = sum(item.total_price_points for item in order.items.all())
        report_data.append({
            'order_id': order.id,
            'date': order.created_at,
            'sponsor': order.organization.name if order.organization else "N/A",
            'driver': order.driver.username,
            'points': points
        })
        total_sales_points += points

    if 'download_csv' in request.GET:
        headers = ['Order ID', 'Date', 'Sponsor Org', 'Driver', 'Points Spent']
        rows = [[d['order_id'], d['date'], d['sponsor'], d['driver'], d['points']] for d in report_data]
        return export_csv("sales_by_sponsor", headers, rows)

    return render(request, 'reports/admin_sales_sponsor.html', {
        'form': form, 
        'report_data': report_data,
        'total_sales': total_sales_points
    })

@login_required
@user_passes_test(is_admin)
def admin_sales_by_driver(request):
    form = AdminSalesDriverForm(request.GET)
    orders = Order.objects.exclude(status='CANCELLED').select_related('driver', 'organization')

    if form.is_valid():
        start, end = get_date_range(form.cleaned_data)
        orders = orders.filter(created_at__date__range=(start, end))
        
        if form.cleaned_data.get('sponsor'):
            orders = orders.filter(organization=form.cleaned_data['sponsor'].organization)
        if form.cleaned_data.get('driver'):
            orders = orders.filter(driver=form.cleaned_data['driver'])

    report_data = []
    for order in orders:
        points = sum(item.total_price_points for item in order.items.all())
        report_data.append({
            'driver': order.driver.username,
            'sponsor': order.organization.name if order.organization else "N/A",
            'date': order.created_at,
            'item_count': order.items.count(),
            'points': points
        })

    if 'download_csv' in request.GET:
        headers = ['Driver', 'Sponsor', 'Date', 'Items', 'Points']
        rows = [[d['driver'], d['sponsor'], d['date'], d['item_count'], d['points']] for d in report_data]
        return export_csv("sales_by_driver", headers, rows)

    return render(request, 'reports/admin_sales_driver.html', {'form': form, 'report_data': report_data})

@login_required
@user_passes_test(is_admin)
def admin_invoice(request):
    form = AdminFilterForm(request.GET)
    invoice_data = []
    
    if form.is_valid():
        start, end = get_date_range(form.cleaned_data)
        
        if form.cleaned_data.get('sponsor'):
            orgs = [form.cleaned_data['sponsor'].organization]
        else:
            orgs = set(Order.objects.filter(created_at__date__range=(start, end)).values_list('organization', flat=True))
            orgs = Organization.objects.filter(id__in=orgs)

        for org in orgs:
            org_orders = Order.objects.filter(
                organization=org, 
                created_at__date__range=(start, end)
            ).exclude(status='CANCELLED')
            
            driver_summaries = {}
            total_points = 0
            
            for order in org_orders:
                p_cost = sum(item.total_price_points for item in order.items.all())
                d_name = order.driver.username
                
                if d_name not in driver_summaries:
                    driver_summaries[d_name] = 0
                driver_summaries[d_name] += p_cost
                total_points += p_cost
            
            total_fee = float(total_points) * float(org.point_value_usd)
            
            invoice_data.append({
                'org_name': org.name,
                'drivers': driver_summaries,
                'total_points': total_points,
                'total_fee': round(total_fee, 2),
                'point_rate': org.point_value_usd
            })

    if 'download_csv' in request.GET:
        headers = ['Organization', 'Driver', 'Points Spent', 'Rate (USD)', 'Fee (USD)']
        rows = []
        for inv in invoice_data:
            for driver, pts in inv['drivers'].items():
                fee = float(pts) * float(inv['point_rate'])
                rows.append([inv['org_name'], driver, pts, inv['point_rate'], round(fee, 2)])
            rows.append([inv['org_name'], 'TOTAL', inv['total_points'], inv['point_rate'], inv['total_fee']])
            rows.append([]) 
        return export_csv("invoices", headers, rows)

    return render(request, 'reports/admin_invoice.html', {'form': form, 'invoices': invoice_data})

@login_required
@user_passes_test(is_admin)
def admin_audit_log(request):
    form = AdminAuditFilterForm(request.GET)
    combined_logs = []
    
    start = datetime(2000, 1, 1).date()
    end = timezone.now().date()
    
    cat = ''
    sponsor_filter = None

    if form.is_valid():
        start, end = get_date_range(form.cleaned_data)
        cat = form.cleaned_data.get('category')
        sponsor_filter = form.cleaned_data.get('sponsor') 
    if not cat or cat == 'login':
        if not sponsor_filter:
            logins = LoginAttempt.objects.filter(timestamp__date__range=(start, end))
            for l in logins:
                combined_logs.append({
                    'type': 'Login',
                    'date': l.timestamp,
                    'actor': l.username,
                    'target': 'System',
                    'details': f"Success: {l.successful} (IP: {l.ip_address})"
                })

    if not cat or cat == 'password':
        if not sponsor_filter:
            pws = PasswordChange.objects.filter(timestamp__date__range=(start, end))
            for p in pws:
                combined_logs.append({
                    'type': 'Password Change',
                    'date': p.timestamp,
                    'actor': p.username,
                    'target': 'Self',
                    'details': "User changed password"
                })

    if not cat or cat == 'profile':
        profs = DriverChangeAudit.objects.filter(date__date__range=(start, end))
        if sponsor_filter:
            profs = profs.filter(sponsor=sponsor_filter.user)
            
        for p in profs:
            combined_logs.append({
                'type': 'Profile Edit',
                'date': p.date,
                'actor': p.sponsor.username if p.sponsor else "System",
                'target': p.driver.username,
                'details': f"{p.field_name}: {p.old_value} -> {p.new_value} ({p.reason})"
            })

    if not cat or cat == 'application':
        apps = DriverApplication.objects.filter(
            updated_at__date__range=(start, end)
        ).exclude(status='pending')
        
        if sponsor_filter:
            apps = apps.filter(sponsor=sponsor_filter)

        for app in apps:
            combined_logs.append({
                'type': 'App Decision',
                'date': app.updated_at,
                'actor': app.sponsor.user.username if app.sponsor else "Unknown",
                'target': app.driver.username,
                'details': f"{app.status.upper()}: {app.message or 'No reason'}"
            })
            
    if not cat or cat == 'point': 
        pts = PointChangeAudit.objects.filter(date__date__range=(start, end))
        if sponsor_filter:
            pts = pts.filter(sponsor=sponsor_filter.user)
            
        for pt in pts:
            combined_logs.append({
                'type': 'Point Change',
                'date': pt.date,
                'actor': pt.sponsor.username if pt.sponsor else "System",
                'target': pt.driver.username,
                'details': f"{pt.point_change_amt} pts. Reason: {pt.reason}"
            })

    combined_logs.sort(key=lambda x: x['date'], reverse=True)

    if 'download_csv' in request.GET:
        headers = ['Type', 'Date', 'Actor/Sponsor', 'Target/Driver', 'Details']
        rows = [[l['type'], l['date'], l['actor'], l['target'], l['details']] for l in combined_logs]
        return export_csv("system_audit_log_full", headers, rows)

    return render(request, 'reports/admin_audit.html', {'form': form, 'logs': combined_logs})