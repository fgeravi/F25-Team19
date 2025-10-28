from django.urls import path
from .views import ack_all_locations
from .views import report_csv

app_name = 'audit'
urlpatterns = [
    path('ack-all/', ack_all_locations, name='ack_all_locations'),
    path('reports/csv/', report_csv, name='report_csv'),
]
