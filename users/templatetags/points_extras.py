from django import template
from django.utils import timezone
from django.db.models import Sum

from users.models import DriverProfile, DriverSponsorPoints

register = template.Library()

@register.simple_tag(takes_context=True)
def total_driver_points(context):
    """
    Returns the combined active points for the logged-in driver
    across ALL sponsors (non-expired).
    """
    user = context.get("user", None)
    if not user or not getattr(user, "is_driver", False):
        return 0

    try:
        driver_profile = user.driverprofile
    except DriverProfile.DoesNotExist:
        return 0

    total = (
        DriverSponsorPoints.objects
        .filter(
            driver_sponsor__driver=driver_profile,
            expiry_at__gt=timezone.now()
        )
        .aggregate(total=Sum("points"))["total"] or 0
    )
    return total