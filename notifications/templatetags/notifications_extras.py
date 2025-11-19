from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def unread_notifications_count(context):
    """
    Returns unread notification count for the current user.
    Safe on anonymous users and if the notifications app isn't ready yet.
    Also ignores archived/hidden notifications if those fields exist.
    """
    user = context.get("user")
    if not user or not getattr(user, "is_authenticated", False):
        return 0

    try:
        qs = user.notifications.all()
        fields = {f.name for f in qs.model._meta.get_fields()}

        if "archived" in fields:
            qs = qs.filter(archived=False)
        if "visible" in fields:
            qs = qs.filter(visible=True)

        if "read_at" in fields:
            qs = qs.filter(read_at__isnull=True)
        elif "is_read" in fields:
            qs = qs.filter(is_read=False)

        return qs.count()
    except Exception:
        return 0