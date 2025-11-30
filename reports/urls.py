from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    # Dashboard / Index
    path('', views.reports_index, name='index'),

    # Sponsor Reports
    path('sponsor/points/', views.sponsor_point_tracking, name='sponsor_point_tracking'),
    path('sponsor/audit/', views.sponsor_audit_log, name='sponsor_audit_log'),

    # Admin Reports
    path('admin/sales-by-sponsor/', views.admin_sales_by_sponsor, name='admin_sales_by_sponsor'),
    path('admin/sales-by-driver/', views.admin_sales_by_driver, name='admin_sales_by_driver'),
    path('admin/invoice/', views.admin_invoice, name='admin_invoice'),
    path('admin/audit/', views.admin_audit_log, name='admin_audit_log'),
]