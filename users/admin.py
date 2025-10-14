from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, SponsorProfile, DriverProfile

# Optional: custom forms if needed
from django import forms
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from .forms import LockedOutAdminAuthenticationForm
from .models import FailedLoginAttempt

admin.site.login_form = LockedOutAdminAuthenticationForm

# --------------------------
# User Forms
# --------------------------
class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "is_sponsor", "is_driver")


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = ("username", "email", "is_sponsor", "is_driver")

# --------------------------
# User Admin
# --------------------------
class UserAdmin(BaseUserAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm

    list_display = ("username", "email", "is_sponsor", "is_driver", "is_staff", "is_superuser")
    list_filter = ("is_sponsor", "is_driver", "is_staff", "is_superuser")
    
    fieldsets = (
        (None, {"fields": ("username", "email", "password")}),
        ("Permissions", {"fields": ("is_sponsor", "is_driver", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "email", "password1", "password2", "is_sponsor", "is_driver", "is_staff", "is_superuser"),
        }),
    )

    search_fields = ("username", "email")
    ordering = ("username",)
    filter_horizontal = ("groups", "user_permissions")

    # SOFT DELETE FEATURE 

    # Disable the default delete button
    def has_delete_permission(self, request, obj=None):
        return False  # No one can delete users
    
    actions = ["hide_users"]

    def hide_users(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(
            request,
            f"{updated} user(s) were successfully hidden.",
            messages.SUCCESS,
        )
    hide_users.short_description = "Hide selected users (deactivate)"

    # hide inactive users by default
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(is_active=True)  # Only show active users


# --------------------------
# Register models
# --------------------------
admin.site.register(User, UserAdmin)
admin.site.register(SponsorProfile)
admin.site.register(DriverProfile)

# --------------------------
# FailedLoginAttempt Admin
# --------------------------
@admin.register(FailedLoginAttempt)
class FailedLoginAttemptAdmin(admin.ModelAdmin):
    list_display = ("created_at", "username", "user_link", "short_ua")
    list_filter = ("created_at",)
    search_fields = ("username", "user_agent", "message")
    date_hierarchy = "created_at"
    readonly_fields = ("created_at", "username", "user", "user_agent", "message")
    actions = ["export_csv"]

    def user_link(self, obj):
        return obj.user.email if getattr(obj.user, 'email', None) else (obj.user or "-")
    user_link.short_description = "User"

    def short_ua(self, obj):
        if not obj.user_agent:
            return "-"
        return (obj.user_agent[:80] + '...') if len(obj.user_agent) > 80 else obj.user_agent
    short_ua.short_description = "User Agent"

    def has_add_permission(self, request):
        return False
    
    def export_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="failed_login_attempts.csv"'
        writer = csv.writer(response)
        writer.writerow(["Created At", "Username", "User", "User Agent", "Message"])
        for row in queryset.iterator():
           writer.writerow([
               row.created_at.isoformat(),
               row.username,
               row.user_id or "",
               (row.user_agent or "").replace("\n", " ")
               (row.message or "").replace("\n", " ")
           ])
        return response
    export_csv.short_description = "Export Selected to CSV"