from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views
from .forms import LockedOutAuthenticationForm
from .views import account_management
from .session_views import extend_session
from .views import AuditedPasswordChangeView


urlpatterns = [
    path("login/", auth_views.LoginView.as_view(
        template_name="users/registration/login.html",
        redirect_authenticated_user=True,
        authentication_form=LockedOutAuthenticationForm,
        success_url='home'
    ), name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="home"), name="logout"),
    path("", views.home, name="home"),
    path("register/", views.register, name="register"),

    # --- Notifications ---
    path("notifications/", views.notifications_list, name="notifications_list"),
    path("notifications/<int:pk>/read/", views.notification_mark_read, name="notification_mark_read"),

    # --- Account Management --- 
    path("account/", account_management, name="account_management"),
    path('manage-drivers/', views.manage_drivers_view, name='manage_drivers'),
    path('manage-drivers/edit/<int:driver_id>/', views.edit_driver_view, name='edit_driver'),
    # Password change views
    path('password-change/', AuditedPasswordChangeView.as_view(), name='password_change'),
    path('password-change/done/', auth_views.PasswordChangeDoneView.as_view(template_name='users/password_change_done.html'), name='password_change_done'),
    
    # --- Session Management ---
    path('extend-session/', extend_session, name='extend_session'),
]