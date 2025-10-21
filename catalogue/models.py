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
    product_id = models.CharField(max_length=100)  # ID from the external API
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    image_url = models.URLField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # New field for "most popular" sorting
    view_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-created_at']  # Default to newest first

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
    viewed_at = models.DateTimeField(auto_now=True)  # Updates every time user views the item

    class Meta:
        ordering = ['-viewed_at']
        unique_together = ['user', 'catalogue_item']  # One record per user-item pair
        indexes = [
            models.Index(fields=['-viewed_at']),
        ]

    def __str__(self):
        return f"{self.user.username} viewed {self.catalogue_item.product_name}"