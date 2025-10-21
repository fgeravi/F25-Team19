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
from .config import LockoutConfig


# ----------------------
# Custom User Model
# ----------------------
class User(AbstractUser):
    is_sponsor = models.BooleanField(default=False)
    is_driver = models.BooleanField(default=False)

    failed_login_attempts = models.PositiveIntegerField(default=0)
    lockout_until = models.DateTimeField(null=True, blank=True)

    def is_locked_out(self) -> bool:
        return bool(self.lockout_until and self.lockout_until > timezone.now())

    def __str__(self):
        return self.username


# ----------------------
# User Profiles
# ----------------------
class SponsorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    company_name = models.CharField(max_length=255)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)

    def __str__(self):
        return f"Sponsor: {self.company_name}"


class DriverProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    license_number = models.CharField(max_length=50)
    vehicle_info = models.CharField(max_length=255)
    current_points = models.PositiveIntegerField(default=0)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"Driver: {self.user.username}"


# ----------------------
# Sponsor Welcome + Notifications
# ----------------------
class SponsorWelcome(models.Model):
    sponsor_org = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        related_name="welcome_config",
        null=True,
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
    driver_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="driver_notifications"
    )
    content = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["-sent_at"]

    def __str__(self):
        return f"Notification<{self.id}> for {self.driver_user.username}"


# ----------------------
# Helper Functions
# ----------------------
def is_sponsor(user) -> bool:
    return getattr(user, "is_sponsor", False)


def is_driver(user) -> bool:
    return getattr(user, "is_driver", False)


def current_welcome_message(org: Organization | None):
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


# ----------------------
# Signals for Profiles
# ----------------------
@receiver(post_save, sender=Organization)
def ensure_org_welcome(sender, instance, created, **kwargs):
    if created:
        SponsorWelcome.objects.get_or_create(sponsor_org=instance)


@receiver(post_save, sender=DriverProfile)
def auto_send_driver_welcome(sender, instance, created, **kwargs):
    if created and instance.user and is_driver(instance.user):
        DriverNotification.objects.create(
            driver_user=instance.user,
            content=current_welcome_message(instance.organization),
            metadata={"type": "welcome"},
        )


# ----------------------
# Lockout Helpers
# ----------------------
def _find_user_by_username(username: str):
    try:
        return User.objects.get(**{User.USERNAME_FIELD: username})
    except User.DoesNotExist:
        return None


def _lockout_attempts() -> int:
    return LockoutConfig.get_config().max_failed_attempts


def _lockout_cooldown_minutes() -> int:
    return LockoutConfig.get_config().lockout_cooldown_minutes


# ----------------------
# Signals: Lockout & Audit
# ----------------------
@receiver(user_login_failed)
def on_login_failed(sender, credentials, request, **kwargs):
    username = (credentials or {}).get("username")
    if not username:
        return

    user = _find_user_by_username(username)

    # Audit logging
    FailedLoginAttempt.objects.create(
        username=username,
        user=user,
        user_agent=request.META.get("HTTP_USER_AGENT") if request else None,
        message="Failed login attempt"
    )

    if not user:
        return

    # Increment failed attempts for ALL users
    if user.lockout_until and user.lockout_until > timezone.now():
        return  # Already locked out

    user.failed_login_attempts += 1

    if user.failed_login_attempts >= _lockout_attempts():
        minutes = _lockout_cooldown_minutes()
        user.lockout_until = (
            timezone.now() + timedelta(minutes=minutes)
            if minutes > 0
            else timezone.now() + timedelta(days=365*100)
        )

    user.save(update_fields=["failed_login_attempts", "lockout_until"])


@receiver(user_logged_in)
def on_login_success(sender, user, request, **kwargs):
    # Reset failed attempts on successful login
    if getattr(user, "failed_login_attempts", 0) or getattr(user, "lockout_until", None):
        user.failed_login_attempts = 0
        user.lockout_until = None
        user.save(update_fields=["failed_login_attempts", "lockout_until"])


# ----------------------
# Audit Log Model
# ----------------------
class FailedLoginAttempt(models.Model):
    username = models.CharField(max_length=254, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    user_agent = models.TextField(null=True, blank=True)
    message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["username"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"FailedLoginAttempt<{self.id}> for '{self.username}' at {self.created_at}"

class DriverChangeAudit(models.Model):
    sponsor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='driver_changes_made'
    )
    driver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile_changes'
    )
    date = models.DateTimeField(auto_now_add=True)
    field_name = models.CharField(max_length=100)
    old_value = models.TextField(blank=True, null=True)
    new_value = models.TextField(blank=True, null=True)
    reason = models.CharField(max_length=255, blank=True, help_text="Optional reason for the change.")

    def __str__(self):
        return f"Change for {self.driver.username} by {self.sponsor.username} on {self.date.strftime('%Y-%m-%d')}"

    class Meta:
        ordering = ['-date']


# Password Audit Events

class PasswordEvent(models.Model):
    EVENT_CHANGE = "password_change"
    EVENT_RESET_REQUESTED = "password_reset_requested"
    EVENT_RESET_SUCCESS = "password_reset_success"
    EVENT_RESET_FAILED = "password_reset_failed"

    EVENT_CHOICES = [
        (EVENT_CHANGE, "Password changed (authenticated)"),
        (EVENT_RESET_REQUESTED, "Password reset requested"),
        (EVENT_RESET_SUCCESS, "Password reset successful"),
        (EVENT_RESET_FAILED, "Password reset failed"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="password_events",
    )
    username = models.CharField(max_length=254, db_index=True, blank=True)
    event_type = models.CharField(max_length=32, choices=EVENT_CHOICES)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["event_type"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        who = self.user.username if self.user else (self.username or "unknown")
        return f"{self.event_type} for {who} at {self.created_at}"