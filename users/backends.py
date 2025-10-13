from django.contrib.auth.backends import ModelBackend
from django.utils import timezone

class LockedoutBackend(ModelBackend):
    def user_can_authenticate(self, user):
        if getattr(user, "lockout_until", None) and user.lockout_until > timezone.now():
            return False
        return super().user_can_authenticate(user)