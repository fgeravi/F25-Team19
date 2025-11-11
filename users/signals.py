from django.contrib.auth.signals import user_login_failed
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import FailedLoginAttempt
from django.utils import timezone
from django.db.models.signals import pre_save
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.utils.timezone import now
from .models import DriverSponsor
from notifications.models import Notification
from django.apps import apps

User = get_user_model()

@receiver(user_login_failed)
def log_failed_login(sender, credentials, request, **kwargs):
    username = credentials.get("username") or credentials.get("email") or ""
    user = None
    if username:
        try:
            user = User.objects.get(**{User.USERNAME_FIELD: username}).first() or \
                User.objects.filter(email=username).first()
        except Exception:
            user = None

    FailedLoginAttempt.objects.create(
        username=username[:254],
        user=user,
        user_agent=(request.META.get("HTTP_USER_AGENT") if request else None),
        message=getattr(request, "_authentication_failure_message", None),
    )

@receiver(pre_save, sender=User)
def update_password_changed_at(sender, instance, **kwargs):
    if instance.pk:
        return
    try:
        old = User.objects.get(pk=instance.pk)
    except User.DoesNotExist:
        return

    if old.password != instance.password:
        instance.password_changed_at = timezone.now()


def _notify(user, title, body, payload=None, org=None):
    if not isinstance(user, User):
        user = getattr(user, "user", None)
    if user is None:
        return

    link = ""
    if isinstance(payload, dict):
        link = payload.get("link", "") or ""

    Notification.objects.create(
        user=user,
        message=str(body)[:255],
        link=link,
    )


@receiver(post_save, sender=DriverSponsor)
def notify_driver_added_to_sponsor(sender, instance: DriverSponsor, created, **kwargs):
    if not created:
        return

    driver_user = getattr(instance.driver, "user", instance.driver)
    sponsor_profile = instance.sponsor
    sponsor_name = (
        getattr(sponsor_profile, "display_name", None)
        or getattr(sponsor_profile, "name", None)
        or sponsor_profile.user.username
    )

    _notify(
        driver_user,
        title="You were added to a sponsor",
        body=f"You’ve been added to sponsor '{sponsor_name}'.",
        payload={
            "type": "driver_sponsor_link",
            "sponsor_id": sponsor_profile.id,
            "action": "added",
        },
        org=getattr(sponsor_profile, "organization", None),
    )


@receiver(pre_delete, sender=DriverSponsor)
def notify_driver_removed_from_sponsor(sender, instance: DriverSponsor, **kwargs):
    driver_user = getattr(instance.driver, "user", instance.driver)
    sponsor_profile = instance.sponsor
    sponsor_name = (
        getattr(sponsor_profile, "display_name", None)
        or getattr(sponsor_profile, "name", None)
        or sponsor_profile.user.username
    )

    _notify(
        driver_user,
        title="You were removed from a sponsor",
        body=f"You were removed from sponsor '{sponsor_name}'.",
        payload={
            "type": "driver_sponsor_link",
            "sponsor_id": sponsor_profile.id,
            "action": "removed",
        },
        org=getattr(sponsor_profile, "organization", None),
    )
