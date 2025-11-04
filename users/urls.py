from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .forms import LockedOutAuthenticationForm
from .views import (
    account_management,
    AuditedPasswordChangeView,
    edit_point_value_view,
)
from .session_views import extend_session
from .reset_views import PasswordResetViewAudit, PasswordResetConfirmViewAudit


urlpatterns = [
    # --- Authentication ---
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="users/registration/login.html",
            redirect_authenticated_user=True,
            authentication_form=LockedOutAuthenticationForm,
            success_url="home",
        ),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(next_page="home"), name="logout"),

    # --- Home & Registration ---
    path("", views.home, name="home"),
    path("register/", views.register, name="register"),

    # --- Notifications (list + mark read) ---
    path("notifications/", views.notifications_list, name="notifications_list"),
    path("notifications/<int:pk>/read/", views.notification_mark_read, name="notification_mark_read"),

    # --- Driver Notification Preferences page ---
    path("account/notifications/", views.notification_preferences, name="notification_preferences"),

    # --- Account Management ---
    path("account/", account_management, name="account_management"),
    path('sponsors/', views.view_sponsors_list, name='view_sponsors_list'),

    # --- Sponsor Management ---
    path("manage-drivers/", views.manage_drivers_view, name="manage_drivers"),
    path("manage-drivers/add/", views.add_driver_view, name="add_driver"),
    path("manage-drivers/import/", views.import_drivers_view, name="import_drivers"),
    path("manage-drivers/add-sponsor/", views.add_sponsor_view, name = "add_sponsor"),
    path("manage-drivers/edit/<int:driver_id>/", views.edit_driver_view, name="edit_driver"),
    path('manage-drivers/export/', views.export_drivers_csv, name='export_drivers_csv'),
    path("account/point-value/", edit_point_value_view, name="edit_point_value"),

    # --- Password Change (while logged in) ---
    path("password-change/", AuditedPasswordChangeView.as_view(), name="password_change"),
    path(
        "password-change/done/",
        auth_views.PasswordChangeDoneView.as_view(
            template_name="users/password_change_done.html"
        ),
        name="password_change_done",
    ),

    # --- Session Management ---
    path("extend-session/", extend_session, name="extend_session"),
]

# --- Password reset (email-to-token flow) ---
urlpatterns += [
    path("password-reset/", PasswordResetViewAudit.as_view(), name="password_reset"),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="users/registration/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path("reset/<uidb64>/<token>/", PasswordResetConfirmViewAudit.as_view(), name="password_reset_confirm"),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="users/registration/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
]