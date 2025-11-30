from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.timezone import now
from django.apps import apps
from django.http import Http404


def _has_field(model, name: str) -> bool:
    """
    True if `name` is a real, concrete field on this model.
    """
    return name in {f.name for f in model._meta.get_fields()}


def _mark_read_fields(obj) -> bool:
    """
    Apply 'read' semantics to a notification object using only
    real DB fields (e.g. read_at, status). Never touches properties
    like `is_read` directly.

    Returns True if anything was changed.
    """
    changed = False
    Model = obj.__class__

    # If the model has a read_at field and it's empty, set it.
    if _has_field(Model, "read_at") and getattr(obj, "read_at", None) is None:
        obj.read_at = now()
        changed = True

    # If there is a status field with choices, try to flip UNREAD/NEW -> READ/OPENED
    if _has_field(Model, "status"):
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
            # Don't let a weird status field blow things up.
            pass

    return changed


def _resolve_model_and_qs(user, archived=None):
    """
    Resolve the concrete notification model and base queryset for the user.

    archived:
        - True  => only archived notifications (if field exists)
        - False or None => only non-archived notifications (default behavior)
    """
    # 1. Prefer the generic Notification model in this app
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
                if archived is True:
                    qs = qs.filter(archived=True)
                else:
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

    # 2. Fallback to DriverNotification in users app
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
                if archived is True:
                    qs = qs.filter(archived=True)
                else:
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

    return None, None


@login_required
def list_notifications(request):
    Model, qs = _resolve_model_and_qs(request.user)
    if Model is None:
        raise Http404("No notifications model configured.")
    return render(request, "notifications/list.html", {"notifications": qs})


@login_required
def mark_all_read(request):
    """
    Bulk mark all notifications as read for this user.
    Only touches real DB fields (read_at, status).
    """
    Model, qs = _resolve_model_and_qs(request.user)
    if Model is None:
        return redirect("notifications:list")

    # Do NOT touch is_read here – it's a property, not a DB field.
    if _has_field(Model, "read_at"):
        qs.filter(read_at__isnull=True).update(read_at=now())

    if _has_field(Model, "status"):
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
    """
    Mark a single notification as read, respecting the user scoping
    from _resolve_model_and_qs.
    """
    Model, qs = _resolve_model_and_qs(request.user)
    if Model is None:
        return redirect("notifications:list")

    # Use qs so we never touch another user's notification.
    n = get_object_or_404(qs, pk=pk)

    if _mark_read_fields(n):
        update_fields = []
        if _has_field(Model, "read_at"):
            update_fields.append("read_at")
        if _has_field(Model, "status"):
            update_fields.append("status")

        n.save(update_fields=update_fields or None)

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

    n = get_object_or_404(qs, pk=pk)
    fields = {f.name for f in Model._meta.get_fields()}

    if "archived" in fields:
        if not getattr(n, "archived", False):
            n.archived = True
            n.save(update_fields=["archived"])
    else:
        # Fallback if the model doesn't support archiving
        n.delete()

    return redirect("notifications:list")


@login_required
def list_archived_notifications(request):
    Model, qs = _resolve_model_and_qs(request.user, archived=True)
    if Model is None:
        raise Http404("No notifications model configured.")
    return render(request, "notifications/list.html", {"notifications": qs})