"""
Access grant and publication tracking models for ReDIB COA portal.
"""

from django.db import models
from django.core.validators import MinValueValidator
from django.conf import settings
from simple_history.models import HistoricalRecords
from applications.models import Application
from core.models import Equipment


class AccessGrant(models.Model):
    """
    DEPRECATED: This model is no longer used as of Phase 7 simplification.

    Acceptance and handoff tracking is now done directly on the Application model
    (see Application.accepted_by_applicant, acceptance_deadline, handoff_email_sent_at).

    This model is kept for historical data only and will be removed in a future version.

    DO NOT create new AccessGrant instances.

    ---

    Legacy model: Granted access after approval (pre-Phase 7)
    """

    application = models.ForeignKey(
        Application,
        on_delete=models.PROTECT,
        related_name='access_grants'
    )
    equipment = models.ForeignKey(
        Equipment,
        on_delete=models.PROTECT,
        related_name='grants'
    )

    hours_granted = models.DecimalField(
        max_digits=6,
        decimal_places=1,
        validators=[MinValueValidator(0)],
        help_text='Hours approved for this equipment'
    )

    # Scheduling
    scheduled_start = models.DateField(null=True, blank=True)
    scheduled_end = models.DateField(null=True, blank=True)

    # Acceptance by user
    accepted_by_user = models.BooleanField(
        null=True,
        blank=True,
        help_text='User accepted the grant'
    )
    accepted_at = models.DateTimeField(null=True, blank=True)
    acceptance_deadline = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Deadline for user to accept'
    )

    # Completion
    completed_at = models.DateTimeField(null=True, blank=True)
    actual_hours_used = models.DecimalField(
        max_digits=6,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text='Actual hours used (reported by node)'
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ['application', 'equipment']
        unique_together = ['application', 'equipment']
        verbose_name = 'Access Grant'

    def __str__(self):
        return f"{self.application.code} - {self.equipment.name}: {self.hours_granted}h"

    @property
    def is_accepted(self):
        """Check if grant was accepted by user"""
        return self.accepted_by_user is True

    @property
    def is_completed(self):
        """Check if access is completed"""
        return self.completed_at is not None

    @property
    def hours_utilization_rate(self):
        """Calculate utilization rate (actual/granted)"""
        if self.actual_hours_used and self.hours_granted:
            return (self.actual_hours_used / self.hours_granted) * 100
        return None


class Publication(models.Model):
    """Publications resulting from COA access"""

    application = models.ForeignKey(
        'applications.Application',
        on_delete=models.CASCADE,
        related_name='publications',
        help_text='Application that resulted in this publication',
        null=True,  # Temporarily nullable for migration
        blank=True
    )

    title = models.CharField(max_length=500)
    authors = models.TextField(blank=True, help_text='List of authors')
    doi = models.CharField(max_length=100, blank=True, help_text='Digital Object Identifier')
    journal = models.CharField(max_length=200, blank=True)
    publication_date = models.DateField(null=True, blank=True)
    publication_year = models.IntegerField(null=True, blank=True)

    # ReDIB acknowledgment
    redib_acknowledged = models.BooleanField(
        default=False,
        help_text='ReDIB properly acknowledged in publication'
    )
    acknowledgment_text = models.TextField(
        blank=True,
        help_text='Acknowledgment text found in publication'
    )

    # Metrics
    citations = models.IntegerField(
        null=True,
        blank=True,
        help_text='Number of citations (if tracked)'
    )
    impact_factor = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        null=True,
        blank=True,
        help_text='Journal impact factor'
    )

    # Reporting
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='publications_reported'
    )
    reported_at = models.DateTimeField(auto_now_add=True)
    verified = models.BooleanField(default=False, help_text='Verified by coordinator')

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ['-publication_date', '-reported_at']

    def __str__(self):
        year = self.publication_year or 'Unpublished'
        return f"{self.title[:50]} ({year})"

    def save(self, *args, **kwargs):
        """Extract publication year from date if not set"""
        if self.publication_date and not self.publication_year:
            self.publication_year = self.publication_date.year
        super().save(*args, **kwargs)
