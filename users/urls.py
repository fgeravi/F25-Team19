from django.urls import path, include 
from django.contrib.auth import views as auth_views
from . import views


urlpatterns = [
    path("login/", auth_views.LoginView.as_view(template_name="Registrations/login.html",  redirect_authenticated_user=True),name="login",),
    path("logout/", auth_views.LogoutView.as_view(next_page="home"), name="logout"),
    path("", views.home, name="home"),
    path('register/', views.register, name='register'),
]