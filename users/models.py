from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """
    Custom user model for project.
    """
    is_sponsor = models.BooleanField(default=False)
    is_driver = models.BooleanField(default=False)

    def __str__(self):
        return self.username


class SponsorProfile(models.Model):
    """
    Profile for sponsor users.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    company_name = models.CharField(max_length=255)
    # future sponsor-specific fields as needed

    def __str__(self):
        return f"Sponsor: {self.company_name}"


class DriverProfile(models.Model):
    """
    Profile for driver users.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    license_number = models.CharField(max_length=50)
    vehicle_info = models.CharField(max_length=255)
    # future driver-specific fields as needed

    def __str__(self):
        return f"Driver: {self.user.username}"
