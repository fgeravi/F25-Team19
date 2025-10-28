from django.db import models

class Organization(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    # NEW: sponsor controlled conversion
    # how many US dollars 1 point is worth.
    # example set up: 0.01 means 1 point = $0.01, 100 points = $1.00
    point_value_usd = models.DecimalField(
        max_digits=6,
        decimal_places=4,
        default=0.01,
        help_text="Dollar value of a single point (ex: 0.01 = 1 point is worth $0.01)"
    )

    def __str__(self):
        return self.name

    def points_to_dollars(self, points: int) -> float:
        """
        Helper so we can display dollar-ish value to drivers.
        This is NOT a binding promise of cash, just reference value.
        """
        if not points:
            return 0.0
        # careful casting to float for display; keep Decimal in DB
        return float(points) * float(self.point_value_usd)