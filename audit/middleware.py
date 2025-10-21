# audit/middleware.py
from django.contrib import messages
from django.utils.html import format_html
from django.urls import reverse

from .models import KnownLoginLocations  

class NewLocationBannerMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.user.is_authenticated
            and (request.user.is_staff or request.user.is_superuser)
            and request.path.startswith('/admin/')
        ):
            # If any unacknowledged location exists for this admin, show a persistent banner
            if KnownLoginLocations.objects.filter(user=request.user, acknowledged=False).exists():
                dismiss_url = reverse('audit:ack_all_locations')
                loc = (KnownLoginLocations.objects
                       .filter(user=request.user, acknowledged=False)
                       .order_by('-first_seen')
                       .first())
                details = [f"IP: {loc.ip_address}"]
                parts = [x for x in [loc.city, loc.region, loc.country] if x]
                if parts:
                    details.append(f"Approx. location: {', '.join(parts)}")

                msg = format_html(
                    "New login detected from a <strong>new location</strong>.<br>{}<br>"
                    "<a href='{}'>Dismiss</a>",
                    format_html("<br>".join(details)),
                    dismiss_url,
                )
                messages.warning(request, msg)

        return self.get_response(request)
