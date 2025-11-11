from django.urls import path
from . import views

urlpatterns = [
    path('report/', views.submit_issue_view, name='submit_issue'),
]