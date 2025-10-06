from django.urls import path
from . import views

app_name = 'rewards'

urlpatterns = [
    path('dashboard/', views.point_dashboard, name='dashboard'),
]