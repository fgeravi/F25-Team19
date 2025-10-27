from django.db import models
from django.conf import settings
from organizations.models import Organization  

class Catalogue(models.Model):
    catalogue_id = models.AutoField(primary_key=True)  # PK
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="catalogues"
    )
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)  # set on creation
    updated_at = models.DateTimeField(auto_now=True)      # updated on every save

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.name} ({self.organization.name})"


class CatalogueItem(models.Model):
    catalogue = models.ForeignKey(Catalogue, on_delete=models.CASCADE, related_name="items")
    product_name = models.CharField(max_length=255)
    product_url = models.URLField()
    product_id = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    image_url = models.URLField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    view_count = models.PositiveIntegerField(default=0)
    category = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.product_name} ({self.catalogue.name})"


# New model to track user's viewing history for "Recently Viewed Items"
class ItemView(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='item_views'
    )
    catalogue_item = models.ForeignKey(
        CatalogueItem,
        on_delete=models.CASCADE,
        related_name='views'
    )
    viewed_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-viewed_at']
        unique_together = ['user', 'catalogue_item']
        indexes = [
            models.Index(fields=['-viewed_at']),
        ]

    def __str__(self):
        return f"{self.user.username} viewed {self.catalogue_item.product_name}"


class CartItem(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cart_items'
    )
    catalogue_item = models.ForeignKey(
        CatalogueItem,
        on_delete=models.CASCADE,
        related_name='in_carts'
    )
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'catalogue_item']
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.user.username}'s cart: {self.catalogue_item.product_name} (x{self.quantity})"
    
    def get_total_price(self):
        if self.catalogue_item.price:
            return self.catalogue_item.price * self.quantity
        return 0