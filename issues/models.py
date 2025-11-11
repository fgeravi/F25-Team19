from django.db import models
from django.conf import settings

class IssueReport(models.Model):
    class Urgency(models.TextChoices):
        LOW = 'LOW', 'Low'
        MEDIUM = 'MEDIUM', 'Medium'
        HIGH = 'HIGH', 'High'

    class Status(models.TextChoices):
        SUBMITTED = 'SUBMITTED', 'Submitted'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        RESOLVED = 'RESOLVED', 'Resolved'
    
    class ReporterRole(models.TextChoices):
        DRIVER = 'DRIVER', 'Driver'
        SPONSOR = 'SPONSOR', 'Sponsor'
        UNKNOWN = 'UNKNOWN', 'Unknown'

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="issue_reports",
        help_text="The user who submitted the report."
    )
    reporter_role = models.CharField(max_length=10, choices=ReporterRole.choices, default=ReporterRole.UNKNOWN)
    
    subject = models.CharField(max_length=255)
    description = models.TextField()
    urgency = models.CharField(max_length=10, choices=Urgency.choices, default=Urgency.LOW)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUBMITTED)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"'{self.subject}' by {self.reporter.username}"