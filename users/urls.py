from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views
from .forms import LockedOutAuthenticationForm


urlpatterns = [
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html",  redirect_authenticated_user=True, authentication_form=LockedOutAuthenticationForm), name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="home"), name="logout"),
    path("", views.home, name="home"),
    path("register/", views.register, name="register"),

    # --- Notifications ---
    path("notifications/", views.notifications_list, name="notifications_list"),
    path("notifications/<int:pk>/read/", views.notification_mark_read, name="notification_mark_read"),
]