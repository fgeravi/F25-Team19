from django.contrib import admin
from .models import Catalogue, CatalogueItem, ItemView, CartItem
from users.models import SponsorProfile 

class SponsorFilter(admin.SimpleListFilter):
    title = "Sponsor"
    parameter_name = "sponsor"

    def lookups(self, request, model_admin):
        sponsors = (
            SponsorProfile.objects
            .select_related("user", "organization")
            .order_by("user__username")
        )
        return [
            (sp.user_id, f"{sp.user.username} ({sp.organization.name})")
            for sp in sponsors
            if sp.organization
        ]

    def queryset(self, request, queryset):
        sponsor_user_id = self.value()
        if not sponsor_user_id:
            return queryset

        model = queryset.model
        if model is Catalogue:
            path = "organization__sponsorprofile__user_id"
        elif model is CatalogueItem:
            path = "catalogue__organization__sponsorprofile__user_id"
        elif model is ItemView:
            path = "catalogue_item__catalogue__organization__sponsorprofile__user_id"
        elif model is CartItem:
            path = "catalogue_item__catalogue__organization__sponsorprofile__user_id"
        else:
            path = "organization__sponsorprofile__user_id"

        return queryset.filter(**{path: sponsor_user_id})


@admin.register(Catalogue)
class CatalogueAdmin(admin.ModelAdmin):
    list_display = ['name', 'sponsor', 'created_at', 'updated_at']
    list_filter = [SponsorFilter, 'sponsor', 'created_at']
    search_fields = ['name', 'sponsor__user__username']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(CatalogueItem)
class CatalogueItemAdmin(admin.ModelAdmin):
    list_display = ['product_name', 'catalogue', 'price', 'is_active', 'view_count', 'created_at']
    list_filter = [SponsorFilter, 'catalogue', 'is_active', 'created_at']
    search_fields = ['product_name', 'product_id', 'catalogue__name']
    readonly_fields = ['created_at', 'view_count']
    list_editable = ['price', 'is_active']
    
    fieldsets = (
        ('Product Information', {
            'fields': ('product_name', 'product_id', 'product_url', 'price', 'is_active')
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
    list_filter = [SponsorFilter, 'viewed_at', 'user']
    search_fields = ['user__username', 'catalogue_item__product_name']
    readonly_fields = ['user', 'catalogue_item', 'viewed_at']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['user', 'catalogue_item', 'quantity', 'get_total_price', 'added_at']
    list_filter = [SponsorFilter, 'added_at', 'user']  
    search_fields = ['user__username', 'catalogue_item__product_name']
    readonly_fields = ['added_at', 'get_total_price']
    list_editable = ['quantity']
    
    def get_total_price(self, obj):
        return f"${obj.get_total_price()}"
    get_total_price.short_description = 'Total Price'
