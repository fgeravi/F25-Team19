from __future__ import annotations
from datetime import timedelta
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.signals import user_login_failed, user_logged_in
from django.utils import timezone
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

    failed_login_attempts = models.PositiveIntegerField(default=0)
    lockout_until = models.DateTimeField(null=True, blank=True)

    def is_locked_out(self) -> bool:
        return bool(self.lockout_until and self.lockout_until > timezone.now())

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
        null=True,  # allow null for default message
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

# Lockout logic for admin/staff users on failed login attempts

def _find_user_by_username(username: str):
    try:
        return User.objects.get(**{User.USERNAME_FIELD: username})
    except User.DoesNotExist:
        return None
    
def _lockout_attempts() -> int:
    return getattr(settings, "MAX_FAILED_LOGIN_ATTEMPTS", 3)

def _lockout_cooldown_minutes() -> int:
    return getattr(settings, "LOCKOUT_COOLDOWN_MINUTES", 5)

@receiver(user_login_failed)
def on_login_failed(sender, credentials, request, **kwargs):
    username = (credentials or {}).get("username")
    if not username:
        return 
    
    user = _find_user_by_username(username)
    if not user:
        return
    
    if not (user.is_staff or user.is_superuser):
        return
    
    if user.lockout_until and user.lockout_until > timezone.now():
        # already locked out
        return
    
    user.failed_login_attempts = (user.failed_login_attempts or 0) + 1

    if user.failed_login_attempts >= _lockout_attempts():
        minutes = _lockout_cooldown_minutes()
        user.lockout_until = (
            timezone.now() + timedelta(minutes=minutes)
            if minutes and minutes > 0
            else timezone.now() + timedelta(days=365*100)  # effectively permanent lockout
        )
    user.save(update_fields=["failed_login_attempts", "lockout_until"])

@receiver(user_logged_in)
def on_login_success(sender, user, request, **kwargs):
    # reset failed attempts on successful login
    if getattr(user, "failed_login_attempts", 0) or getattr(user, "lockout_until", None):
        user.failed_login_attempts = 0
        user.lockout_until = None
        user.save(update_fields=["failed_login_attempts", "lockout_until"])