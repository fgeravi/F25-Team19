from django.contrib.auth.backends import ModelBackend
from django.utils import timezone

class LockedoutBackend(ModelBackend):
    def user_can_authenticate(self, user):
        if getattr(user, "lockout_until", None) and user.lockout_until > timezone.now():
            return False
        return super().user_can_authenticate(user)

    def authenticate(self, request, username=None, password=None, **kwargs):
        user = super().authenticate(request, username, password, **kwargs)
        if user and request and hasattr(request, 'session'):
            if 'remember_me' in request.POST:
                from django.conf import settings
                request.session['remember_me'] = True
                request.session.set_expiry(settings.EXTENDED_SESSION_LENGTH)
            else:
                request.session['remember_me'] = False
                request.session.set_expiry(0)
        return user