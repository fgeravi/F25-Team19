from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required

@login_required
def extend_session(request):
    """Extend the user's session."""
    from django.utils import timezone
    from django.conf import settings
    
    # Clear all existing messages first
    storage = messages.get_messages(request)
    for _ in storage:
        pass  # Iterate through to mark all messages as used
    
    # Reset the session timers
    request.session['last_activity'] = timezone.now().timestamp()
    request.session['_session_init_timestamp_'] = timezone.now().timestamp()
    request.session.pop('timeout_warning_shown', None)
    
    # Set appropriate expiry
    if request.session.get('remember_me', False):
        request.session.set_expiry(settings.EXTENDED_SESSION_LENGTH)
    else:
        request.session.set_expiry(settings.SESSION_COOKIE_AGE)
    
    messages.success(request, 'Session extended.', extra_tags='safe')
    return redirect(request.META.get('HTTP_REFERER', 'home'))