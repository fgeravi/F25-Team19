from django.urls import path
from .views import ack_all_locations, report_csv, audit_log_report

app_name = 'audit'
urlpatterns = [
    path('ack-all/', ack_all_locations, name='ack_all_locations'),
    path('reports/csv/', report_csv, name='report_csv'),
    path('reports/log/', audit_log_report, name='audit_log_report'),
]
