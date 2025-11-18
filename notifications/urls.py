from django.urls import path
from . import views

app_name = "notifications"

urlpatterns = [
    path("", views.list_notifications, name="list"),
    path("read-all/", views.mark_all_read, name="read_all"),
    path("<int:pk>/read/", views.mark_one_read, name="read_one"),
    path("<int:pk>/archive/", views.archive_notification, name="archive"),

    # NEW: list archived notifications
    path("archived/", views.list_archived_notifications, name="archived_list"),
]