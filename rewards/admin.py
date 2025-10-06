from django.contrib import admin
from .models import PointChangeAudit

@admin.register(PointChangeAudit)
class PointChangeAuditAdmin(admin.ModelAdmin):
    """
    Customizes the admin interface for the PointChangeAudit model.
    """
    list_display = (
        'date', 
        'driver', 
        'sponsor', 
        'organization', 
        'point_change_amt', 
        'new_point_balance'
    )
    list_filter = ('organization', 'sponsor', 'driver')
    search_fields = (
        'driver__username', 
        'sponsor__username', 
        'reason'
    )
    # Makes the admin page read-only. An audit log should never be changed.
    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False
# Register your models here.
