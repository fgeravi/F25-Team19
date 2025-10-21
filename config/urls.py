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

admin.site.login_form = LockedOutAdminAuthenticationForm
admin.site.site_header = "F25 Team 19 Admin (v{})".format(settings.APP_VERSION)
admin.site.site_title = "Dashboard - v{}".format(settings.APP_VERSION)
admin.site.site_title = "F25 Team 19 Admin"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("users.urls")),
    path("about/", about_page, name="about"), 
    path('rewards/', include('rewards.urls')),
    path("apply/", include("applications.urls")),
]
