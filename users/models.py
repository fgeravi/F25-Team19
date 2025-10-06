from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

class User(AbstractUser):
    """
    Custom user model for project.
    """
    is_sponsor = models.BooleanField(default=False)
    is_driver = models.BooleanField(default=False)

    def __str__(self):
        return self.username


class SponsorProfile(models.Model):
    """
    Profile for sponsor users.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    company_name = models.CharField(max_length=255)
    # future sponsor-specific fields as needed

    def __str__(self):
        return f"Sponsor: {self.company_name}"


class DriverProfile(models.Model):
    """
    Profile for driver users.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    license_number = models.CharField(max_length=50)
    vehicle_info = models.CharField(max_length=255)
    # future driver-specific fields as needed

    def __str__(self):
        return f"Driver: {self.user.username}"


# Sponsor Welcome + Notifications

class SponsorWelcome(models.Model):
    # On/Off setting, show only to new users
    sponsor_user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="welcome_config"
    )
    is_active = models.BooleanField(default=True)
    welcome_text = models.TextField(
        default="Welcome to the Good Driver Incentive Program! We’re excited to have you onboard.",
        blank=True,
    )

    def __str__(self):
        return f"Welcome message by {self.sponsor_user.username}"


class DriverNotification(models.Model):
    # In-app notifs
    driver_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="driver_notifications"
    )
    content = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"Notification<{self.id}> for {self.driver_user.username}"


# Helper functions

def is_sponsor(user) -> bool:
    return getattr(user, "is_sponsor", False)

def is_driver(user) -> bool:
    return getattr(user, "is_driver", False)

def current_welcome_message():
    # Send out saved message
    sponsor_entry = SponsorWelcome.objects.filter(is_active=True).first()
    if sponsor_entry and sponsor_entry.welcome_text.strip():
        return sponsor_entry.welcome_text.strip()
    return "Welcome aboard!"


# Signals


@receiver(post_save, sender=User)
def ensure_sponsor_welcome(sender, instance, created, **kwargs):
    # Ensure user has a corresponding welcome settings row
    if created and is_sponsor(instance):
        SponsorWelcome.objects.get_or_create(sponsor_user=instance)


@receiver(post_save, sender=User)
def auto_send_driver_welcome(sender, instance, created, **kwargs):
    # Create a welcome notification using the current sponsor message
    if created and is_driver(instance):
        DriverNotification.objects.create(
            driver_user=instance,
            content=current_welcome_message(),
            metadata={"type": "welcome"},
        )