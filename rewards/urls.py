from django.urls import path
from . import views

app_name = 'rewards'

urlpatterns = [
    path('dashboard/', views.point_dashboard, name='dashboard'),
    path('add-points/', views.add_points_view, name='add_points'),

    # Generating reports
    path('reports/points/', views.points_tracking_report, name='points_report'),
    path('reports/points/export.csv', views.points_tracking_csv, name='points_report_csv'),
]