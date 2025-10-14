from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.dispatch import receiver
from .models import LoginAttempt

@receiver(user_logged_in)
def log_successful_login(sender, request, user, **kwargs):
    LoginAttempt.objects.create(
        username=user.username,
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        successful=True
    )

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
