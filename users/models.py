from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from organizations.models import Organization


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
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
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
    # Added points field that is not in the ERD, so that points are tracked live rather than having to refer to audit log history to sum up points
    current_points = models.PositiveIntegerField(default=0)
    # driver is affiliated with one sponsor organization
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True, blank=True)
    # future driver-specific fields as needed

    def __str__(self):
        return f"Driver: {self.user.username}"


# Sponsor Welcome + Notifications

class SponsorWelcome(models.Model):
    # One message per sponsor organization
    sponsor_org = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        related_name="welcome_config",
    )
    is_active = models.BooleanField(default=True)
    welcome_text = models.TextField(
        default="Welcome to the Good Driver Incentive Program! We’re excited to have you onboard.",
        blank=True,
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Welcome message for {self.sponsor_org.name}"


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
    # NEW: mark-as-read support
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["-sent_at"]

    def __str__(self):
        return f"Notification<{self.id}> for {self.driver_user.username}"


# Helper functions

def is_sponsor(user) -> bool:
    return getattr(user, "is_sponsor", False)

def is_driver(user) -> bool:
    return getattr(user, "is_driver", False)

def current_welcome_message(org: Organization | None):
    # return the active org message if set, else any active message, else default
    if org:
        try:
            sw = SponsorWelcome.objects.get(sponsor_org=org, is_active=True)
            txt = (sw.welcome_text or "").strip()
            if txt:
                return txt
        except SponsorWelcome.DoesNotExist:
            pass
    sw = SponsorWelcome.objects.filter(is_active=True).first()
    if sw and (sw.welcome_text or "").strip():
        return sw.welcome_text.strip()
    return "Welcome aboard!"


# Signals

@receiver(post_save, sender=Organization)
def ensure_org_welcome(sender, instance, created, **kwargs):
    # ensure each sponsor organization gets a welcome config row
    if created:
        SponsorWelcome.objects.get_or_create(sponsor_org=instance)


@receiver(post_save, sender=DriverProfile)
def auto_send_driver_welcome(sender, instance, created, **kwargs):
    # when a driver profile is created, send a welcome message from their sponsor org
    if created and instance.user and is_driver(instance.user):
        DriverNotification.objects.create(
            driver_user=instance.user,
            content=current_welcome_message(instance.organization),
            metadata={"type": "welcome"},
        )