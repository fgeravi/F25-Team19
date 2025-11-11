from django.contrib import admin
from .models import IssueReport

@admin.register(IssueReport)
class IssueReportAdmin(admin.ModelAdmin):
    list_display = ('subject', 'reporter', 'reporter_role', 'status', 'urgency', 'created_at')
    list_filter = ('status', 'urgency', 'reporter_role', 'created_at')
    search_fields = ('subject', 'description', 'reporter__username')
    date_hierarchy = 'created_at'
    
    readonly_fields = ('reporter', 'reporter_role', 'created_at', 'updated_at')
    
    fieldsets = (
        (None, {
            'fields': ('subject', 'description', 'reporter', 'reporter_role')
        }),
        ('Admin', {
            'fields': ('status', 'urgency')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )