from django.contrib.auth.signals import user_login_failed
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import FailedLoginAttempt

User = get_user_model()

@receiver(user_login_failed)
def log_failed_login(sender,credentials, request, **kwargs):
    username = credentials.get("username") or credentials.get("email") or ""
    user = None
    if username:
        try:
            user = User.objects.get(**{User.USERNAME_FIELD: username}).first() or \
                User.objects.filter(email=username).first()
        except Exception:
            user = None

    FailedLoginAttempt.objects.create(
        username=username[:254], 
        user=user,
        user_agent=(request.META.get("HTTP_USER_AGENT") if request else None),
        message=getattr(request, "_authentication_failure_message", None),
    )
    