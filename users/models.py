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
from notifications.models import Notification
from django.urls import reverse


# ----------------------
# Custom User Model
# ----------------------
class User(AbstractUser):
    is_sponsor = models.BooleanField(default=False)
    is_driver = models.BooleanField(default=False)

    failed_login_attempts = models.PositiveIntegerField(default=0)
    lockout_until = models.DateTimeField(null=True, blank=True)
    password_changed_at = models.DateTimeField(null=True, blank=True)

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
    # Expiration policy (in days)
    points_expiration_days = models.PositiveIntegerField(default=90, help_text="Number of days points are valid for drivers")

    notify_on_100_points = models.BooleanField(default=False,help_text="Notify me when any of my drivers reaches 100 points.")

    def __str__(self):
        return f"{self.user.username} ({self.organization.name})"


class DriverProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    license_number = models.CharField(max_length=50)
    vehicle_info = models.CharField(max_length=255)
    current_points = models.PositiveIntegerField(default=0)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True, blank=True)

    # notification preferences
    notify_points_change = models.BooleanField(default=True)
    notify_order_placed = models.BooleanField(default=True)
    # note: dropped-by-sponsor cant be disabled, so we don't have a flag for it

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
        # guard against null org names
        name = getattr(self.sponsor_org, "name", "Unknown Org")
        return f"Welcome message for {name}"


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
    # NEW: support soft-delete/archive
    archived = models.BooleanField(default=False)

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
        send_driver_notification(
            driver_user=instance.user,
            content=current_welcome_message(instance.organization),
            notif_type="welcome",
            metadata_extra={},
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
        message="Failed login attempt",
    )

    if not user:
        return

    try:
        ip_address = request.META.get("REMOTE_ADDR") if request else None
        ip_display = ip_address or "an unknown location"

        message = f"Failed login attempt on your account from {ip_display}."

        try:
            link = reverse("audit:audit_log_report") 
        except Exception:
            link = ""

        Notification.objects.create(
            user=user,
            message=message,
            link=link,
        )
    except Exception:
        pass

    # Increment failed attempts for ALL users
    if user.lockout_until and user.lockout_until > timezone.now():
        return 

    user.failed_login_attempts += 1

    if user.failed_login_attempts >= _lockout_attempts():
        minutes = _lockout_cooldown_minutes()
        user.lockout_until = (
            timezone.now() + timedelta(minutes=minutes)
            if minutes > 0
            else timezone.now() + timedelta(days=365 * 100)
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


def send_driver_notification(driver_user, content, notif_type, metadata_extra=None):
    """
    Central place to send a driver notification with respect to their preferences.

    notif_type should be one of:
    - "dropped"                (cannot be disabled)
    - "points_change"          (can be disabled by driver)
    - "order_placed"           (can be disabled by driver)
    - "order_cancelled"        (uses the same preference as order_placed)
    - "welcome"                (welcome message, send unconditionally is fine)
    """
    if not driver_user or not getattr(driver_user, "is_driver", False):
        return  # not a driver, skip

    try:
        profile = driver_user.driverprofile
    except DriverProfile.DoesNotExist:
        profile = None

    # Enforce rules
    if notif_type == "dropped":
        allow = True  # cannot be disabled
    elif notif_type == "points_change":
        allow = profile.notify_points_change if profile else True
    elif notif_type in ("order_placed", "order_cancelled"):
        allow = profile.notify_order_placed if profile else True
    else:
        # default safe behavior: send
        allow = True

    if not allow:
        return

    Notification.objects.create(
        user=driver_user,
        message=content,
        link=(metadata_extra or {}).get("link", ""),
    )

# --------------------------------
# SponsorDriver relationship model
# --------------------------------
class DriverSponsor(models.Model):
    driver = models.ForeignKey(
        "DriverProfile",
        on_delete=models.CASCADE,
        related_name="sponsorships"
    )
    sponsor = models.ForeignKey(
        "SponsorProfile",
        on_delete=models.CASCADE,
        related_name="drivers"
    )
    approved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("driver", "sponsor")

    @property
    def points(self) -> int:
        # sum non-expired points
        return sum(pe.points for pe in self.point_entries.filter(expiry_at__gt=timezone.now()))


    def __str__(self):
        return f"{self.driver.user.username} ↔ {self.sponsor.company_name}"
    
def add_points(driver_sponsor: DriverSponsor, points: int):
    # Use sponsor's expiration policy
    expiry_days = driver_sponsor.sponsor.points_expiration_days
    expiry = timezone.now() + timedelta(days=expiry_days)
    
    DriverSponsorPoints.objects.create(
        driver_sponsor=driver_sponsor,
        points=points,
        expiry_at=expiry
    )
    
    send_driver_notification(
        driver_user=driver_sponsor.driver.user,
        content=f"You received {points} points from {driver_sponsor.sponsor.company_name}. They will expire in {expiry_days} days.",
        notif_type="points_change"
    )

def expire_points():
    now = timezone.now()
    expired_entries = DriverSponsorPoints.objects.filter(expiry_at__lte=now)
    for entry in expired_entries:
        entry.delete() 
        send_driver_notification(
            driver_user=entry.driver_sponsor.driver.user,
            content=f"Some of your points from {entry.driver_sponsor.sponsor.company_name} have expired.",
            notif_type="points_change"
        )



class DeletionAuditLog(models.Model):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        help_text="The user who performed the deletion.",
        related_name="deletions_performed"
    )
    deleted_user_id = models.IntegerField()
    deleted_user_username = models.CharField(max_length=150)
    deleted_user_role = models.CharField(max_length=50, blank=True)
    reason = models.TextField(blank=True, help_text="Optional reason for deletion.")
    deleted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-deleted_at']

    def __str__(self):
        actor_name = getattr(self.actor, 'username', 'System')
        return f"User '{self.deleted_user_username}' deleted by '{actor_name}' at {self.deleted_at}"
    
class DriverSponsorPoints(models.Model):
    driver_sponsor = models.ForeignKey(
        "DriverSponsor",
        on_delete=models.CASCADE,
        related_name="point_entries"
    )
    points = models.PositiveIntegerField(default=0)
    awarded_at = models.DateTimeField(auto_now_add=True)
    expiry_at = models.DateTimeField()

    def is_expired(self) -> bool:
        from django.utils import timezone
        return timezone.now() >= self.expiry_at


