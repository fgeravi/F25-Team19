"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from about.views import about_page
from users.forms import LockedOutAdminAuthenticationForm
from django.conf import settings
from django.contrib.auth import views as auth_views

admin.site.login_form = LockedOutAdminAuthenticationForm
admin.site.site_header = "F25 Team 19 Admin (v{})".format(settings.APP_VERSION)
admin.site.site_title = "Dashboard - v{}".format(settings.APP_VERSION)
admin.site.site_title = "F25 Team 19 Admin"

urlpatterns = [
    path("admin/", admin.site.urls),

    # Root routing first goes to users.urls
    path("", include("users.urls")),

    path("about/", about_page, name="about"),
    path("rewards/", include("rewards.urls")),
    path("apply/", include("applications.urls")),
    path("catalog/", include("catalogue.urls")),
    path("audit/", include(("audit.urls", "audit"), namespace="audit")),
    path("issues/", include("issues.urls")),

    # Password change
    path(
        "accounts/password/change/",
        auth_views.PasswordChangeView.as_view(),
        name="password_change",
    ),
    path(
        "accounts/password/change/done/",
        auth_views.PasswordChangeDoneView.as_view(),
        name="password_change_done",
    ),

    # NEW SYSTEM — notifications app (must not be shadowed by users.urls)
    path("notifications/", include("notifications.urls")),

    # Hijack admin tool
    path("hijack/", include("hijack.urls")),
]