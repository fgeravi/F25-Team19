from django.db import models
from django.conf import settings
from organizations.models import Organization
from users.models import SponsorProfile 

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

    sponsor = models.ForeignKey(
        SponsorProfile,
        on_delete=models.CASCADE,
        related_name="applications",
        null=True
    )

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("driver", "sponsor")  # prevent duplicate apps

    def __str__(self):
        return f"{self.driver.username} → {self.sponsor.user.username} ({self.status})"
