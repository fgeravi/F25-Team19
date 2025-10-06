from django.contrib import admin
from .models import Organization

# register Organization to admin portal
@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "created_at", "is_active")
    search_fields = ("name", "email")
    list_filter = ("is_active",)
