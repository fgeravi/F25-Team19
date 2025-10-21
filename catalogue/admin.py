from django.contrib import admin
from .models import Catalogue, CatalogueItem, ItemView


@admin.register(Catalogue)
class CatalogueAdmin(admin.ModelAdmin):
    list_display = ['name', 'organization', 'created_at', 'updated_at']
    list_filter = ['organization', 'created_at']
    search_fields = ['name', 'organization__name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(CatalogueItem)
class CatalogueItemAdmin(admin.ModelAdmin):
    list_display = ['product_name', 'catalogue', 'price', 'view_count', 'created_at']
    list_filter = ['catalogue', 'created_at']
    search_fields = ['product_name', 'product_id', 'catalogue__name']
    readonly_fields = ['created_at', 'view_count']
    list_editable = ['price']
    
    fieldsets = (
        ('Product Information', {
            'fields': ('product_name', 'product_id', 'product_url', 'price')
        }),
        ('Catalog', {
            'fields': ('catalogue',)
        }),
        ('Media', {
            'fields': ('image_url',)
        }),
        ('Statistics', {
            'fields': ('view_count', 'created_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ItemView)
class ItemViewAdmin(admin.ModelAdmin):
    list_display = ['user', 'catalogue_item', 'viewed_at']
    list_filter = ['viewed_at', 'user']
    search_fields = ['user__username', 'catalogue_item__product_name']
    readonly_fields = ['user', 'catalogue_item', 'viewed_at']
    
    def has_add_permission(self, request):
        # Prevent manual creation of views in admin
        return False
    
    def has_change_permission(self, request, obj=None):
        # Make views read-only in admin
        return False
