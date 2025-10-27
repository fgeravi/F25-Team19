from django.contrib import admin
from .models import Catalogue, CatalogueItem, ItemView, CartItem


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
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['user', 'catalogue_item', 'quantity', 'get_total_price', 'added_at']
    list_filter = ['added_at', 'user']
    search_fields = ['user__username', 'catalogue_item__product_name']
    readonly_fields = ['added_at', 'get_total_price']
    list_editable = ['quantity']
    
    def get_total_price(self, obj):
        return f"${obj.get_total_price()}"
    get_total_price.short_description = 'Total Price'
