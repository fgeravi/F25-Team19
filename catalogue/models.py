from django.db import models
from organizations.models import Organization  # assuming you already have an Organization model

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
