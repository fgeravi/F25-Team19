from django.urls import path
from . import views

app_name = 'rewards'

urlpatterns = [
    path('dashboard/', views.point_dashboard, name='dashboard'),
    path('add-points/', views.add_points_view, name='add_points'),
    path('api/get-driver-points/<int:driver_id>/', views.get_driver_points, name='get_driver_points_api'),

    # Generating reports
    path('reports/points/', views.points_tracking_report, name='points_report'),
    path('reports/points/export.csv', views.points_tracking_csv, name='points_report_csv'),
]