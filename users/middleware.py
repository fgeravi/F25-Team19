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
            # Get the timestamp of last activity
            last_activity = request.session.get('last_activity')
            now = timezone.now().timestamp()
            inactive_time = 0  # Initialize to 0

            if last_activity:
                # Calculate time since last activity
                inactive_time = now - float(last_activity)

                # Get session timeout
                session_timeout = request.session.get('_session_init_timestamp_')
                if session_timeout is None:
                    # Initialize session timestamp on first activity
                    request.session['_session_init_timestamp_'] = now
                    session_timeout = now

                elapsed_time = now - float(session_timeout)
                expiry = request.session.get_expiry_age()

                # Show warning when 1 minute remains
                if expiry > 0:  # Only show warning for timed sessions
                    warning_time = expiry - 60  # 1 minute before expiry
                    if elapsed_time > warning_time and not request.session.get('timeout_warning_shown', False):
                        # Clear any existing timeout messages first
                        storage = messages.get_messages(request)
                        for message in storage:
                            if 'session will expire' in str(message) or 'session has been extended' in str(message):
                                storage.used = True
                        storage.used = False
                        
                        messages.warning(request, 
                            f'Your session will expire soon. <a href="{reverse("extend_session")}">Click here to extend</a>',
                            extra_tags='safe'
                        )
                        request.session['timeout_warning_shown'] = True

                # Check for session expiry
                if expiry > 0 and elapsed_time > expiry:
                    messages.info(request, 'Your session has expired due to inactivity.')
                    request.session.flush()
                    return redirect(f'{reverse("login")}?next={request.path}')
            
            # Update last activity timestamp
            request.session['last_activity'] = now
            
            # Clear warning flag if activity is detected and last warning was more than 1 minute ago
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
            and (user.is_staff or user.is_superuser)  # Only enforce for admin users
            and not _is_path_allowed(path)
        ):
            max_age_days = getattr(settings, "PASSWORD_MAX_AGE_DAYS", 90)
            cutoff = timezone.now() - timedelta(days=max_age_days)

            expired = (
                not user.password_changed_at 
                or user.password_changed_at < cutoff
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