from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.dispatch import receiver
from .models import LoginAttempt
from django.conf import settings
from django.utils import timezone
from django.utils.html import format_html
from django.contrib import messages 
from .models import LoginAttempt, KnownLoginLocations

@receiver(user_logged_in)
def log_successful_login(sender, request, user, **kwargs):
    ip = get_client_ip(request)
    ua = request.META.get('HTTP_USER_AGENT', '')
    
    LoginAttempt.objects.create(
        username=user.username,
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        successful=True
    )

    notify_admins_only = getattr(settings, "NEW_LOGIN_NOTIFY_ADMINS_ONLY", True)
    if notify_admins_only:
        is_admin = bool(getattr(user, "is_superuser", False) or getattr(user, "is_staff", False))
    if notify_admins_only and not is_admin:
        return
    
    fingetprint = KnownLoginLocations.fingerprint(ip)
    city, region, country = geo_lookup(ip)

    obj, created = KnownLoginLocations.objects.get_or_create(
        user = user,
        ip_fingerprint = fingetprint,
        defaults={
            'ip_address': ip,
            'city': city or None,
            'region': region or None,
            'country': country or None,
        },
    )

    if not created:
        changed = False
        if obj.ip_address != ip:
            obj.ip_address = ip
            changed = True
        if (city and not obj.city) or (region and not obj.region) or (country and not obj.country):
            obj.city = obj.city or (city or None)
            obj.region = obj.region or (region or None)
            obj.country = obj.country or (country or None)
            changed = True
        if changed:
            obj.save(update_fields=['ip_address', 'city', 'region', 'country', 'last_seen'])
        return
    
    msg = format_html(
        "New login detected from a <strong>new location</strong>.<br>"
        "IP: {}{}<br>User-Agent: {}",
        ip,
        _render_xff_suffix(request),
        ua,
    )
    messages.warning(request, msg)

@receiver(user_login_failed)
def log_failed_login(sender, credentials, request, **kwargs):
    LoginAttempt.objects.create(
        username=credentials.get('username', ''),
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        successful=False
    )

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')

def _render_xff_suffix(request):
    if not request:
        return ""
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    return f" (XFF: {xff})" if xff else ""

def geo_lookup(ip):
    city = region = country = ""
    try:
        from django.contrib.gis.geoip2 import GeoIP2
        g = GeoIP2()
        rec = g.city(ip)
        city = rec.get("city", "")
        region = rec.get("region", "")
        country = rec.get("country_name", "")
    except Exception:
        pass
    return city, region, country
