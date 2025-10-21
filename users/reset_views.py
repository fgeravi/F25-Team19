from django.contrib.auth import get_user_model, views as auth_views
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.debug import sensitive_post_parameters
from django.http import HttpRequest

from .models import PasswordEvent

User = get_user_model()


def _client_ip(req: HttpRequest) -> str | None:
    xff = req.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        parts = [p.strip() for p in xff.split(",")]
        if parts:
            return parts[0]
    return req.META.get("REMOTE_ADDR")


def _ua(req: HttpRequest) -> str | None:
    return req.META.get("HTTP_USER_AGENT")


class PasswordResetViewAudit(auth_views.PasswordResetView):
    """
    Request reset link. Always shows generic success.
    Logs 'password_reset_requested' with user if resolvable by email.
    """
    template_name = "users/registration/password_reset_form.html"
    email_template_name = "users/registration/password_reset_email.txt"
    subject_template_name = "users/registration/password_reset_subject.txt"
    success_url = reverse_lazy("password_reset_done")

    @method_decorator(sensitive_post_parameters("email"))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def form_valid(self, form):
        email = form.cleaned_data.get("email")
        user = None
        if email:
            try:
                user = User.objects.get(email__iexact=email)
            except User.DoesNotExist:
                user = None

        PasswordEvent.objects.create(
            user=user,
            username=(user.username if user else (email or "")),
            event_type=PasswordEvent.EVENT_RESET_REQUESTED,
            ip_address=_client_ip(self.request),
            user_agent=_ua(self.request),
        )
        return super().form_valid(form)


class PasswordResetConfirmViewAudit(auth_views.PasswordResetConfirmView):
    """
    Set the new password via token.
    Logs success or failed (invalid/expired token or validation errors).
    """
    template_name = "users/registration/password_reset_confirm.html"
    success_url = reverse_lazy("password_reset_complete")

    @method_decorator(sensitive_post_parameters("new_password1", "new_password2"))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def form_valid(self, form):
        resp = super().form_valid(form)
        user = getattr(self, "user", None)
        PasswordEvent.objects.create(
            user=user,
            username=(user.username if user else ""),
            event_type=PasswordEvent.EVENT_RESET_SUCCESS,
            ip_address=_client_ip(self.request),
            user_agent=_ua(self.request),
        )
        return resp

    def form_invalid(self, form):
        user = getattr(self, "user", None)
        PasswordEvent.objects.create(
            user=user,
            username=(user.username if user else ""),
            event_type=PasswordEvent.EVENT_RESET_FAILED,
            ip_address=_client_ip(self.request),
            user_agent=_ua(self.request),
        )
        return super().form_invalid(form)