from django.urls import path
from .views import ack_all_locations

app_name = 'audit'
urlpatterns = [
    path('ack-all/', ack_all_locations, name='ack_all_locations'),
]
