# rewards/context_processors.py

from django.apps import apps


def header_points(request):
    """
    Provide header_total_points for any authenticated driver so we can
    show it in the top nav on every page.

    Logic:
    - If user is not logged in or not a driver → 0.
    - Otherwise, find the PointChangeAudit model dynamically and use the
      latest new_point_balance for this driver.
    """
    user = getattr(request, "user", None)

    if not (getattr(user, "is_authenticated", False) and getattr(user, "is_driver", False)):
        return {"header_total_points": 0}

    # Dynamically find the PointChangeAudit model by class name
    PointChangeAudit = None
    for m in apps.get_models():
        if m.__name__ == "PointChangeAudit":
            PointChangeAudit = m
            break

    # If we somehow can't find it, just return 0 instead of crashing
    if PointChangeAudit is None:
        return {"header_total_points": 0}

    # Get most recent audit entry for this driver (newest by date/id)
    latest = (
        PointChangeAudit.objects
        .filter(driver=user)
        .order_by("-date", "-id")
        .first()
    )

    total = getattr(latest, "new_point_balance", 0) if latest else 0
    return {"header_total_points": total or 0}