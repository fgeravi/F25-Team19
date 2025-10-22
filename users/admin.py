from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from .forms import LockedOutAdminAuthenticationForm
from .models import (
    User,
    SponsorProfile,
    DriverProfile,
    FailedLoginAttempt,
    DriverChangeAudit,
)
from .config import LockoutConfig
from audit.models import PasswordChange

# Set custom login form for admin
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
# Inline Profiles
# --------------------------
class SponsorProfileInline(admin.StackedInline):
    model = SponsorProfile
    can_delete = False
    fk_name = "user"
    verbose_name = "Sponsor Profile"
    verbose_name_plural = "Sponsor Profile"
    autocomplete_fields = ("organization",)
    extra = 0


class DriverProfileInline(admin.StackedInline):
    model = DriverProfile
    can_delete = False
    fk_name = "user"
    verbose_name = "Driver Profile"
    verbose_name_plural = "Driver Profile"
    autocomplete_fields = ("organization",)
    extra = 0


# --------------------------
# User Admin
# --------------------------
class UserAdmin(BaseUserAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm

    list_display = (
        "username",
        "email",
        "is_sponsor",
        "is_driver",
        "is_staff",
        "is_superuser",
        "failed_login_attempts",
        "lockout_status",
        "lockout_until",
    )
    list_filter = ("is_sponsor", "is_driver", "is_staff", "is_superuser")

    fieldsets = (
        (None, {"fields": ("username", "email", "password")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_sponsor",
                    "is_driver",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "email",
                    "password1",
                    "password2",
                    "is_sponsor",
                    "is_driver",
                    "is_staff",
                    "is_superuser",
                ),
            },
        ),
    )

    search_fields = ("username", "email")
    ordering = ("username",)
    filter_horizontal = ("groups", "user_permissions")
    actions = ["hide_users", "unlock_users"]

    # --------------------------
    # Inline logic
    # --------------------------
    def get_inline_instances(self, request, obj=None):
        inlines = []
        if obj:
            if obj.is_sponsor:
                inlines.append(SponsorProfileInline(self.model, self.admin_site))
            if obj.is_driver:
                inlines.append(DriverProfileInline(self.model, self.admin_site))
        return inlines

    # --------------------------
    # Custom columns
    # --------------------------
    def lockout_status(self, obj):
        return obj.is_locked_out()
    lockout_status.boolean = True
    lockout_status.short_description = "Locked Out?"

    # --------------------------
    # Soft delete
    # --------------------------
    def has_delete_permission(self, request, obj=None):
        return False

    def hide_users(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(
            request, f"{updated} user(s) were successfully hidden.", messages.SUCCESS
        )
    hide_users.short_description = "Hide selected users (deactivate)"

    # --------------------------
    # Unlock action
    # --------------------------
    def unlock_users(self, request, queryset):
        updated = queryset.update(lockout_until=None, failed_login_attempts=0)
        self.message_user(
            request, f"{updated} user(s) were successfully unlocked.", messages.SUCCESS
        )
    unlock_users.short_description = "Unlock selected users"

    # --------------------------
    # Show only active users
    # --------------------------
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(is_active=True)


# --------------------------
# Lockout Config Admin
# --------------------------
@admin.register(LockoutConfig)
class LockoutConfigAdmin(admin.ModelAdmin):
    list_display = ("max_failed_attempts", "lockout_cooldown_minutes", "updated_at")
    readonly_fields = ("updated_at",)

    def has_add_permission(self, request):
        return not LockoutConfig.objects.exists()


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
        return obj.user.email if getattr(obj.user, "email", None) else (obj.user or "-")
    user_link.short_description = "User"

    def short_ua(self, obj):
        if not obj.user_agent:
            return "-"
        return (obj.user_agent[:80] + "...") if len(obj.user_agent) > 80 else obj.user_agent
    short_ua.short_description = "User Agent"

    def has_add_permission(self, request):
        return False

    def export_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="failed_login_attempts.csv"'
        writer = csv.writer(response)
        writer.writerow(["Created At", "Username", "User", "User Agent", "Message"])
        for row in queryset.iterator():
            writer.writerow(
                [
                    row.created_at.isoformat(),
                    row.username,
                    row.user_id or "",
                    (row.user_agent or "").replace("\n", " "),
                    (row.message or "").replace("\n", " "),
                ]
            )
        return response
    export_csv.short_description = "Export Selected to CSV"


# --------------------------
# DriverChangeAudit Admin
# --------------------------
@admin.register(DriverChangeAudit)
class DriverChangeAuditAdmin(admin.ModelAdmin):
    list_display = ("date", "sponsor", "driver", "field_name", "old_value", "new_value")
    list_filter = ("date", "sponsor", "driver")
    search_fields = ("sponsor__username", "driver__username")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# --------------------------
# PasswordChange Admin
# --------------------------
@admin.register(PasswordChange)
class PasswordChangeAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "username", "user_link", "short_ua")
    list_filter = ("timestamp",)
    search_fields = ("username", "user_agent")
    date_hierarchy = "timestamp"
    readonly_fields = ("timestamp", "username", "ip_address", "user_agent")

    def user_link(self, obj):
        return obj.username
    user_link.short_description = "User"

    def short_ua(self, obj):
        if not obj.user_agent:
            return "-"
        return (obj.user_agent[:80] + "...") if len(obj.user_agent) > 80 else obj.user_agent
    short_ua.short_description = "User Agent"

    def has_add_permission(self, request):
        return False


# --------------------------
# Register main models
# --------------------------
admin.site.register(User, UserAdmin)
admin.site.register(SponsorProfile)
admin.site.register(DriverProfile)
