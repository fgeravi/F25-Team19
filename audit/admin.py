from datetime import timedelta
from django.contrib import admin
from django.utils import timezone
from django.db import models

from .models import LoginAttempt


def _find_datetime_field(model):
    preferred = (
        "when",
        "timestamp",
        "created_at",
        "attempted_at",
        "date",
        "datetime",
        "time",
        "login_time",
    )
    for name in preferred:
        try:
            f = model._meta.get_field(name)
            if isinstance(f, (models.DateTimeField, models.DateField)):
                return name
        except Exception:
            pass
    for f in model._meta.get_fields():
        if isinstance(f, (models.DateTimeField, models.DateField)):
            return f.name
    return None


def _has_field(model, name):
    try:
        model._meta.get_field(name)
        return True
    except Exception:
        return False


class TimeWindowListFilter(admin.SimpleListFilter):
    title = "Time window"
    parameter_name = "window"

    WINDOWS = {
        "5m": 5 * 60,
        "15m": 15 * 60,
        "1h": 60 * 60,
        "24h": 24 * 60 * 60,
        "all": None,
    }

    def lookups(self, request, model_admin):
        return [
            ("5m", "Last 5 minutes"),
            ("15m", "Last 15 minutes"),
            ("1h", "Last 1 hour"),
            ("24h", "Last 24 hours"),
            ("all", "All"),
        ]

    def queryset(self, request, queryset):
        key = self.value()
        if not key:
            return queryset
        seconds = self.WINDOWS.get(key)
        if seconds is None:
            return queryset

        dt_field = getattr(self, "dt_field", None)
        if not dt_field:
            self.dt_field = dt_field = _find_datetime_field(queryset.model)

        if not dt_field:
            return queryset

        since = timezone.now() - timedelta(seconds=seconds)
        return queryset.filter(**{f"{dt_field}__gte": since})


@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    BASE_DISPLAY = ("username", "ip_address", "user_agent")

    def get_list_display(self, request):
        fields = []
        dt_field = _find_datetime_field(self.model)
        if dt_field:
            fields.append(dt_field)
        for name in ("username", "ip_address", "success", "user_agent"):
            if _has_field(self.model, name):
                fields.append(name)
        return tuple(dict.fromkeys(fields or self.BASE_DISPLAY))

    def get_list_filter(self, request):
        filters = [TimeWindowListFilter]
        if _has_field(self.model, "success"):
            filters.append("success")
        return tuple(filters)

    def get_date_hierarchy(self, request):
        return _find_datetime_field(self.model)

    search_fields = ("username", "ip_address", "user_agent")
