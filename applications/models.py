from django.db import models
from django.conf import settings
from organizations.models import Organization

# ------------------------
# DriverApplication Model
# ------------------------
class DriverApplication(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("denied", "Denied"),
    ]

    driver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        limit_choices_to={"is_driver": True},
        on_delete=models.CASCADE,
        related_name="applications"
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="applications"
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    message = models.TextField(blank=True, null=True)  # Optional message from driver

    class Meta:
        unique_together = ("driver", "organization")  # Prevent duplicate applications

    def __str__(self):
        return f"{self.driver.username} → {self.organization.name} ({self.status})"
