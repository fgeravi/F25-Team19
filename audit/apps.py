# audit/apps.py
from django.apps import AppConfig
from django.db.models.signals import post_migrate

def _create_download_perms(sender, **kwargs):
    # Import inside the function to avoid early app/model import
    from django.contrib.auth.models import Group, Permission
    from django.contrib.contenttypes.models import ContentType
    from django.apps import apps

    # Use a model that exists in the 'audit' app as the permission anchor
    Report = apps.get_model("audit", "Report")  # make sure you have audit.models.Report (tiny placeholder is fine)
    if Report is None:
        return  # safety

    ct = ContentType.objects.get_for_model(Report)

    sponsor_perm, _ = Permission.objects.get_or_create(
        codename="can_download_reports",
        name="Can download sponsor reports",
        content_type=ct,
    )
    driver_perm, _ = Permission.objects.get_or_create(
        codename="can_download_own_reports",
        name="Can download own driver reports",
        content_type=ct,
    )

    sponsors, _ = Group.objects.get_or_create(name="Sponsors")
    sponsors.permissions.add(sponsor_perm)
    drivers, _ = Group.objects.get_or_create(name="Drivers")
    drivers.permissions.add(driver_perm)

class AuditConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "audit"

    def ready(self):
        post_migrate.connect(_create_download_perms, sender=self)
