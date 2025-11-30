# rewards/context_processors.py

from users.models import DriverProfile, DriverSponsor


def header_points(request):
    """
    Provide header_total_points for the nav bar.

    We mirror the default behavior of the rewards dashboard:
    - Look up this driver's approved sponsorships
    - Pick the *first* sponsorship (same as dashboard default)
    - Use its `.points` property as the current balance

    That way the value in the top-right header matches the
    "Current Point Balance" you see on the Points page.
    """
    user = request.user

    # Only drivers get a header points badge
    if not user.is_authenticated or not getattr(user, "is_driver", False):
        return {}

    try:
        driver_profile = user.driverprofile
    except DriverProfile.DoesNotExist:
        return {}

    # Same sponsorship query style as in point_dashboard
    sponsorships = (
        DriverSponsor.objects
        .filter(driver=driver_profile, approved=True)
        .select_related("sponsor__user", "sponsor__organization")
        .order_by("created_at")
    )

    selected_ds = sponsorships.first()
    if not selected_ds:
        total = 0
    else:
        # DriverSponsor typically exposes a `.points` property
        total = getattr(selected_ds, "points", 0) or 0

    return {
        "header_total_points": total,
    }