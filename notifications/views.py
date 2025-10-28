from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.timezone import now
from .models import Notification

@login_required
def list_notifications(request):
    qs = Notification.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "notifications/list.html", {"notifications": qs})

@login_required
def mark_all_read(request):
    Notification.objects.filter(user=request.user, read_at__isnull=True).update(read_at=now())
    return redirect("notifications:list")

@login_required
def mark_one_read(request, pk):
    n = get_object_or_404(Notification, pk=pk, user=request.user)
    if n.read_at is None:
        n.read_at = now()
        n.save(update_fields=["read_at"])
    return redirect("notifications:list")
