from django.utils import timezone
from django.shortcuts import redirect
from django.contrib import messages
from django.conf import settings
from django.urls import reverse
from datetime import timedelta
from django.urls import reverse


class SessionTimeoutMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            last_activity = request.session.get('last_activity')
            now = timezone.now().timestamp()
            inactive_time = 0

            if last_activity:
                inactive_time = now - float(last_activity)

                session_timeout = request.session.get('_session_init_timestamp_')
                if session_timeout is None:
                    request.session['_session_init_timestamp_'] = now
                    session_timeout = now

                elapsed_time = now - float(session_timeout)
                expiry = request.session.get_expiry_age()

                if expiry > 0:
                    warning_time = expiry - 60
                    if elapsed_time > warning_time and not request.session.get('timeout_warning_shown', False):
                        storage = messages.get_messages(request)
                        for message in storage:
                            if 'session will expire' in str(message) or 'session has been extended' in str(message):
                                storage.used = True
                        storage.used = False
                        
                        messages.warning(
                            request, 
                            f'Your session will expire soon. <a href="{reverse("extend_session")}">Click here to extend</a>',
                            extra_tags='safe'
                        )
                        request.session['timeout_warning_shown'] = True

                if expiry > 0 and elapsed_time > expiry:
                    messages.info(request, 'Your session has expired due to inactivity.')
                    request.session.flush()
                    return redirect(f'{reverse("login")}?next={request.path}')
            
            request.session['last_activity'] = now
            
            if request.session.get('timeout_warning_shown') and inactive_time < 840:
                del request.session['timeout_warning_shown']

        response = self.get_response(request)
        return response
    
def _is_path_allowed(path: str) -> bool:
    allow = getattr(settings, "PASSWORD_GRACE_ALLOWLIST", [])
    return any(path.startswith(p) for p in allow)

class EnforcePasswordRotationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        path = request.path

        if (
            user 
            and user.is_authenticated
            and (user.is_staff or user.is_superuser)
            and not _is_path_allowed(path)
        ):
            max_age_days = getattr(settings, "PASSWORD_MAX_AGE_DAYS", 90)
            cutoff = timezone.now() - timedelta(days=max_age_days)

            changed_at = getattr(user, "password_changed_at", None)
            treat_unknown = getattr(settings, "PASSWORD_TREAT_UNKNOWN_AS_EXPIRED", False)
            expired = (
                (changed_at is not None and changed_at < cutoff)
                or (changed_at is None and treat_unknown)
            )

            if expired:
                try: 
                    change_url = reverse('password_change')
                except Exception:
                    change_url = getattr(settings, "PASSWORD_CHANGE_URL", "/accounts/password/change/")

                if path != change_url:
                    messages.warning(
                        request,
                        f"Your password has expired (>{max_age_days} days). Please change your password to continue."
                    )
                    return redirect(change_url)

        response = self.get_response(request)
        return response
