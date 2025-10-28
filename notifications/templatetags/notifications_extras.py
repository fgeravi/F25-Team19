from django import template

register = template.Library()

@register.simple_tag(takes_context=True)
def unread_notifications_count(context):
    """
    Returns unread notification count for the current user.
    Safe on anonymous users and if the notifications app isn't ready yet.
    """
    user = context.get("user")
    if not user or not getattr(user, "is_authenticated", False):
        return 0
    try:
        return user.notifications.filter(read_at__isnull=True).count()
    except Exception:
        return 0
