from django.contrib import admin
from .models import DriverApplication

@admin.register(DriverApplication)
class DriverApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "driver",
        "get_sponsor_username",
        "get_sponsor_org_name",
        "status",
        "created_at",
        "updated_at"
    )
    list_filter = ("status", "sponsor__organization")
    search_fields = ("driver__username", "sponsor__user__username", "sponsor__organization__name", "message")
    readonly_fields = ("created_at", "updated_at")
    list_editable = ("status",)

    def get_sponsor_username(self, obj):
        return obj.sponsor.user.username
    get_sponsor_username.short_description = "Sponsor"

    def get_sponsor_org_name(self, obj):
        return obj.sponsor.organization.name if obj.sponsor.organization else "-"
    get_sponsor_org_name.short_description = "Sponsor Organization"
