from django.db import models
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.urls import reverse

from organizations.models import Organization
from users.models import (
    SponsorProfile,
    DriverNotification,
    DriverSponsor,
    DriverSponsorPoints,
    add_points,
)
from notifications.models import Notification


class PointChangeAudit(models.Model):
    # Not on ERD, but added to track which organization the sponsor was in when points were awarded.
    # Avoids data integrity issues if a sponsor changes organizations, as it does not rely on current sponsor profile.
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name='point_audits'
    )
    date = models.DateTimeField(auto_now_add=True)
    sponsor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='awarded_point_audits'
    )
    driver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_point_audits'
    )
    point_change_amt = models.IntegerField()
    reason = models.CharField(max_length=255, blank=True)
    new_point_balance = models.IntegerField()

    def __str__(self):
        sponsor_name = self.sponsor.username if self.sponsor else "[Sponsor Deleted]"
        return f"Audit for {self.driver.username} by {sponsor_name} on {self.date.strftime('%Y-%m-%d')}"

    class Meta:
        ordering = ['-date']


def award_points_to_driver(sponsor_user, driver_user, points, reason=""):
    """
    Atomically adjust the sponsor-specific driver balance,
    write an audit row, and send in-app notifications.

    Uses DriverSponsor.points for balances.
    """
    try:
        with transaction.atomic():
            # Ensure sponsor profile exists
            sponsor_profile = SponsorProfile.objects.select_for_update().get(user=sponsor_user)
            organization = sponsor_profile.organization

            # Ensure driver is linked to this sponsor (and lock the row for concurrent safety)
            ds = DriverSponsor.objects.select_for_update().get(
                sponsor=sponsor_profile,
                driver=driver_user.driverprofile,
                approved=True,
            )

            # Balance before change
            old_balance = ds.points

            # Apply the change via DriverSponsorPoints
            if points > 0:
                add_points(ds, points)
            elif points < 0:
                to_deduct = -points
                if old_balance < to_deduct:
                    raise ValueError("Point balance cannot be negative.")
                _deduct_points(ds, to_deduct)

            # Balance after change
            new_balance = ds.points

            # Write audit with sponsor-specific new balance
            audit = PointChangeAudit.objects.create(
                organization=organization,
                driver=driver_user,
                sponsor=sponsor_user,
                point_change_amt=points,
                reason=reason,
                new_point_balance=new_balance,
            )

            THRESHOLD = 100

            if points > 0 and getattr(sponsor_profile, "notify_on_100_points", False):
                # Fire when we cross from below 100 to at/over 100
                if old_balance < THRESHOLD <= new_balance:
                    driver_name = driver_user.get_full_name() or driver_user.username
                    message = f"{driver_name} has reached {THRESHOLD} points."

                    try:
                        link = reverse("rewards:points_report") + f"?driver={driver_user.id}"
                    except Exception:
                        link = ""

                    Notification.objects.create(
                        user=sponsor_user,
                        message=message,
                        link=link,
                    )

            if points <= 0:
                sign = "+" if points >= 0 else ""
                sponsor_name = sponsor_user.username if sponsor_user else "Sponsor"
                content = f"{sign}{points} points from {sponsor_name}: {reason or 'No reason provided'}"
                DriverNotification.objects.create(
                    driver_user=driver_user,
                    content=content,
                    metadata={
                        "type": "points_change",
                        "audit_id": audit.id,
                        "new_balance": new_balance,
                        "organization_id": organization.id if organization else None,
                    },
                )

        return True, "Points updated and driver notified."

    except SponsorProfile.DoesNotExist:
        return False, "Sponsor profile not found."
    except DriverSponsor.DoesNotExist:
        return False, "Driver is not linked to this sponsor."
    except ValueError as e:
        return False, str(e)
    except Exception as e:
        return False, f"An unexpected error occurred: {str(e)}"


    
def _deduct_points(driver_sponsor: DriverSponsor, amount: int):
    """
    Deduct `amount` points from this DriverSponsor's non-expired entries,
    consuming from the soonest-to-expire points first.
    Raises ValueError if not enough points are available.
    """
    if amount <= 0:
        return

    remaining = amount

    # Only non-expired entries, soonest expiry first
    entries = (
        DriverSponsorPoints.objects
        .filter(driver_sponsor=driver_sponsor, expiry_at__gt=timezone.now())
        .order_by("expiry_at", "id")
    )

    for entry in entries:
        if remaining <= 0:
            break

        if entry.points > remaining:
            entry.points -= remaining
            entry.save(update_fields=["points"])
            remaining = 0
        else:
        # consume the whole entry
            remaining -= entry.points
            entry.delete()

    if remaining > 0:
        # Tried to deduct more than exists
        raise ValueError("Point balance cannot be negative.")


# Create your models here.