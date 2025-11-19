from django.conf import settings
from django.db import models

class Notification(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    message = models.CharField(max_length=255)
    link = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    # Soft-delete / archive flag so we can hide notifications instead of fully deleting
    # These can later be permanently deleted after ~60 days via a cleanup job.
    archived = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    @property
    def is_read(self):
        return self.read_at is not None


from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.timezone import now
from django.apps import apps
from django.http import Http404


def _has_field(model, name: str) -> bool:
    return name in {f.name for f in model._meta.get_fields()}


def _resolve_model_and_qs(user):
    try:
        DN = apps.get_model("users", "DriverNotification")
        fields = {f.name: f for f in DN._meta.get_fields()}
        qs = None
        driver_profile = getattr(user, "driverprofile", None)

        if "driver" in fields and getattr(fields["driver"], "remote_field", None):
            if driver_profile is None:
                qs = DN.objects.none()
            else:
                qs = DN.objects.filter(driver=driver_profile)
        elif "user" in fields:
            qs = DN.objects.filter(user=user)
        elif "recipient" in fields:
            qs = DN.objects.filter(recipient=user)
        elif "owner" in fields:
            qs = DN.objects.filter(owner=user)

        if qs is not None:
            if _has_field(DN, "archived"):
                qs = qs.filter(archived=False)
            if _has_field(DN, "visible"):
                qs = qs.filter(visible=True)

            if _has_field(DN, "created_at"):
                qs = qs.order_by("-created_at")
            elif _has_field(DN, "created"):
                qs = qs.order_by("-created")
            elif _has_field(DN, "timestamp"):
                qs = qs.order_by("-timestamp")
            else:
                qs = qs.order_by("-id")

            return DN, qs
    except LookupError:
        pass

    try:
        N = apps.get_model("notifications", "Notification")
        fields = {f.name for f in N._meta.get_fields()}
        qs = None

        if "user" in fields:
            qs = N.objects.filter(user=user)
        elif "recipient" in fields:
            qs = N.objects.filter(recipient=user)
        elif "owner" in fields:
            qs = N.objects.filter(owner=user)

        if qs is not None:
            if "archived" in fields:
                qs = qs.filter(archived=False)
            if "visible" in fields:
                qs = qs.filter(visible=True)

            if "created_at" in fields:
                qs = qs.order_by("-created_at")
            elif "created" in fields:
                qs = qs.order_by("-created")
            elif "timestamp" in fields:
                qs = qs.order_by("-timestamp")
            else:
                qs = qs.order_by("-id")

            return N, qs
    except LookupError:
        pass

    return None, None


def _mark_read_fields(obj) -> bool:
    """
    Sets 'read' semantics on the object if those fields exist.
    Returns True if anything changed.
    """
    changed = False

    if hasattr(obj, "is_read") and not getattr(obj, "is_read"):
        obj.is_read = True
        changed = True

    if hasattr(obj, "read_at") and getattr(obj, "read_at") is None:
        obj.read_at = now()
        changed = True

    if hasattr(obj, "status"):
        try:
            field = obj._meta.get_field("status")
            choices = {c[0] for c in getattr(field, "choices", [])}
            cur = getattr(obj, "status", None)
            if cur in {"NEW", "UNREAD"}:
                if "READ" in choices:
                    obj.status = "READ"
                    changed = True
                elif "OPENED" in choices:
                    obj.status = "OPENED"
                    changed = True
        except Exception:
            pass

    return changed


@login_required
def list_notifications(request):
    Model, qs = _resolve_model_and_qs(request.user)
    if Model is None:
        raise Http404("No notifications model configured.")
    return render(request, "notifications/list.html", {"notifications": qs})


@login_required
def mark_all_read(request):
    Model, qs = _resolve_model_and_qs(request.user)
    if Model is None:
        return redirect("notifications:list")

    fields = {f.name for f in Model._meta.get_fields()}

    if "is_read" in fields:
        qs.update(is_read=True)
    if "read_at" in fields:
        qs.filter(read_at__isnull=True).update(read_at=now())
    if "status" in fields:
        try:
            choices = {c[0] for c in Model._meta.get_field("status").choices}
            if "READ" in choices:
                qs.update(status="READ")
            elif "OPENED" in choices:
                qs.update(status="OPENED")
        except Exception:
            pass

    return redirect("notifications:list")


@login_required
def mark_one_read(request, pk):
    Model, qs = _resolve_model_and_qs(request.user)
    if Model is None:
        return redirect("notifications:list")

    n = get_object_or_404(qs.model, pk=pk)

    if _mark_read_fields(n):
        to_update = [
            name for name in ("is_read", "read_at", "status") if hasattr(n, name)
        ]
        n.save(update_fields=to_update if to_update else None)

    return redirect("notifications:list")


@login_required
def archive_notification(request, pk):
    """
    Soft-delete / archive a notification instead of permanently deleting it.
    If the underlying model does not support 'archived', fall back to hard delete.
    """
    Model, qs = _resolve_model_and_qs(request.user)
    if Model is None:
        return redirect("notifications:list")

    n = get_object_or_404(qs.model, pk=pk)
    fields = {f.name for f in Model._meta.get_fields()}

    if "archived" in fields:
        if not getattr(n, "archived", False):
            n.archived = True
            n.save(update_fields=["archived"])
    else:
        # Fallback if the model doesn't support archiving
        n.delete()

    return redirect("notifications:list")