# catalogue/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.urls import reverse
from django.contrib.auth import get_user_model

from notifications.models import Notification
from users.models import DriverProfile
from .models import CatalogueItem

User = get_user_model()

def _notify_org_drivers(org, message):
    driver_ids = DriverProfile.objects.filter(organization=org).values_list("user_id", flat=True)
    users = User.objects.filter(id__in=driver_ids, is_active=True)

    try:
        link = reverse("catalogue:view_catalogue", kwargs={"org_id": org.id})
    except Exception:
        link = ""

    Notification.objects.bulk_create(
        [Notification(user=u, message=message, link=link) for u in users.iterator()],
        batch_size=500
    )

@receiver(post_save, sender=CatalogueItem)
def notify_item_saved(sender, instance, created, **kwargs):
    org = getattr(instance.catalogue, "organization", None)
    if not org:
        return
    msg = f"New catalog item added: {instance.product_name}" if created else f"Catalog item updated: {instance.product_name}"
    _notify_org_drivers(org, msg)

@receiver(post_delete, sender=CatalogueItem)
def notify_item_deleted(sender, instance, **kwargs):
    org = getattr(instance.catalogue, "organization", None)
    if not org:
        return
    _notify_org_drivers(org, f"Catalog item removed: {getattr(instance, 'product_name', 'Item')}")
