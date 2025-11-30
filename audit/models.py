from django.db import models
from django.conf import settings
import ipaddress
from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.dispatch import receiver


# audit model for login attempts
class LoginAttempt(models.Model):
    username = models.CharField(max_length=150)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    successful = models.BooleanField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.username} - {'Success' if self.successful else 'Failed'} at {self.timestamp}"

# audit model for password changes
class PasswordChange(models.Model):
    username = models.CharField(max_length=150)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.username} - Changed password at {self.timestamp}"

# audit model for known login locations   
class KnownLoginLocations(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='known_login_locations')
    ip_address = models.GenericIPAddressField()
    ip_fingerprint = models.CharField(max_length=64, db_index=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    region = models.CharField(max_length=100, null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)
    acknowledged = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'ip_fingerprint') # Ensure unique fingerprint per user

    def __str__(self):
        return f"{self.user} @ {self.ip_fingerprint}" # Display user and fingerprint
    
    @staticmethod
    def fingerprint(ip_str: str) -> str:
        try:
            ip = ipaddress.ip_address(ip_str) # Parse IP address
        except ValueError: 
            return ip_str  # Return original if invalid IP
        if isinstance(ip, ipaddress.IPv4Address):
            parts = ip_str.split('.')
            return '.'.join(parts[:3]) + '.*'
        else:
            parts = ip_str.split(':') # Handle IPv6
            parts += ['0'] * (8 - len(parts))
            return ':'.join(parts[:4]) + ':*'
        
class Report(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Report"
        
@receiver(user_logged_in)
def log_successful_login(sender, request, user, **kwargs):
    """
    Listens for successful logins and records them in the Audit Log.
    """
    ip = request.META.get('REMOTE_ADDR')
    ua = request.META.get('HTTP_USER_AGENT')
    
    LoginAttempt.objects.create(
        username=user.username,
        ip_address=ip,
        user_agent=ua,
        successful=True
    )

@receiver(user_login_failed)
def log_failed_login(sender, credentials, request, **kwargs):
    """
    Listens for failed logins and records them in the Audit Log.
    (This ensures they show up in your Admin Audit Report)
    """
    username = credentials.get('username', 'unknown') if credentials else 'unknown'
    ip = request.META.get('REMOTE_ADDR')
    ua = request.META.get('HTTP_USER_AGENT')
    
    LoginAttempt.objects.create(
        username=username,
        ip_address=ip,
        user_agent=ua,
        successful=False
    )