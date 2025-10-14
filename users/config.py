from django.db import models


# config for lockout protocol 
class LockoutConfig(models.Model):
    max_failed_attempts = models.PositiveIntegerField(default=3)
    lockout_cooldown_minutes = models.PositiveIntegerField(default=5)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.max_failed_attempts} attempts → {self.lockout_cooldown_minutes} min lockout"

    class Meta:
        verbose_name = "Lockout Configuration"
        verbose_name_plural = "Lockout Configuration"

    @classmethod
    def get_config(cls):
        # Return existing or default configuration
        config, _ = cls.objects.get_or_create(id=1)
        return config
