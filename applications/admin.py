from django.contrib import admin
from .models import DriverApplication

@admin.register(DriverApplication)
class DriverApplicationAdmin(admin.ModelAdmin):
    list_display = ("driver", "organization", "status", "created_at", "updated_at")
    list_filter = ("status", "organization")
    search_fields = ("driver__username", "organization__name", "message")
    readonly_fields = ("created_at", "updated_at")

    # Allow editing 'status' and 'message' directly from the list view
    list_editable = ("status",)
