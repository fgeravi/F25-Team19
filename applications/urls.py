from django.urls import path
from . import views

urlpatterns = [
    # Driver applies to an organization
    path("", views.apply_to_organization, name="apply_to_organization"),

    # Sponsor views applications for their org
    path("applications/", views.sponsor_view_applications, name="sponsor_applications"),

    # Sponsor approves/denies
    path("applications/<int:app_id>/update/", views.update_application_status, name="update_application_status"),

    # Driver view own applications
    path("my-applications/", views.driver_applications_list, name="driver_applications_list"),
]
