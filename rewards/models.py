from django.db import models
from django.conf import settings
from django.db import transaction
from organizations.models import Organization
from users.models import SponsorProfile, DriverNotification, DriverSponsor  # <-- added DriverSponsor import

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
    Atomically adjust the sponsor-specific driver balance (DriverSponsor.points),
    write an audit row, and send an in-app notification.

    This enforces that the driver is linked to the sponsor (approved=True) and
    prevents balances from going negative.
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
                approved=True
            )

            # Compute new sponsor-specific balance
            new_balance = ds.points + points
            if new_balance < 0:
                raise ValueError("Point balance cannot be negative.")

            # Persist the new balance on the DriverSponsor relation
            ds.points = new_balance
            ds.save(update_fields=["points"])

            # Write audit with sponsor-specific new balance
            audit = PointChangeAudit.objects.create(
                organization=organization,
                driver=driver_user,
                sponsor=sponsor_user,
                point_change_amt=points,
                reason=reason,
                new_point_balance=new_balance
            )

            # Send in-app notification to the driver
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
# Create your models here.