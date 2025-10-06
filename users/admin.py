from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, SponsorProfile, DriverProfile

# Optional: custom forms if needed
from django import forms
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

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


# --------------------------
# Register models
# --------------------------
admin.site.register(User, UserAdmin)
admin.site.register(SponsorProfile)
admin.site.register(DriverProfile)
