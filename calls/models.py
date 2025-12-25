"""
Call management models for ReDIB COA portal.
"""

from django.db import models
from django.core.validators import MinValueValidator
from simple_history.models import HistoricalRecords
from core.models import Equipment


class Call(models.Model):
    """COA Call periods"""

    CALL_STATUSES = [
        ('draft', 'Draft'),
        ('open', 'Open for Submissions'),
        ('closed', 'Closed - Under Evaluation'),
        ('resolved', 'Resolved'),
    ]

    code = models.CharField(
        max_length=20,
        unique=True,
        help_text='e.g., COA-2025-01'
    )
    title = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=CALL_STATUSES, default='draft')

    # Important dates
    submission_start = models.DateTimeField()
    submission_end = models.DateTimeField()
    evaluation_deadline = models.DateTimeField()
    execution_start = models.DateTimeField(help_text='When experiments can begin')
    execution_end = models.DateTimeField(help_text='When experiments must end')

    # Content
    description = models.TextField(help_text='Call description (HTML allowed)')
    guidelines = models.TextField(blank=True, help_text='Application guidelines')

    # Publication
    published_at = models.DateTimeField(null=True, blank=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ['-submission_start']
        verbose_name = 'COA Call'

    def __str__(self):
        return f"{self.code} - {self.title}"

    @property
    def is_open(self):
        """Check if call is currently accepting submissions"""
        from django.utils import timezone
        now = timezone.now()
        return (
            self.status == 'open' and
            self.submission_start <= now <= self.submission_end
        )

    @property
    def total_hours_offered(self):
        """Calculate total hours offered across all equipment"""
        return self.equipment_allocations.aggregate(
            total=models.Sum('hours_offered')
        )['total'] or 0


class CallEquipmentAllocation(models.Model):
    """Hours offered per equipment per call"""

    call = models.ForeignKey(
        Call,
        on_delete=models.CASCADE,
        related_name='equipment_allocations'
    )
    equipment = models.ForeignKey(
        Equipment,
        on_delete=models.CASCADE,
        related_name='call_allocations'
    )
    hours_offered = models.DecimalField(
        max_digits=6,
        decimal_places=1,
        validators=[MinValueValidator(0)],
        help_text='Total hours available for this call'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ['call', 'equipment']
        unique_together = ['call', 'equipment']
        verbose_name = 'Equipment Allocation'

    def __str__(self):
        return f"{self.call.code} - {self.equipment.name}: {self.hours_offered}h"

    @property
    def hours_allocated(self):
        """Calculate hours already allocated to accepted applications"""
        from applications.models import RequestedAccess, Application
        return RequestedAccess.objects.filter(
            equipment=self.equipment,
            application__call=self.call,
            application__resolution='accepted'
        ).aggregate(
            total=models.Sum('hours_requested')
        )['total'] or 0

    @property
    def hours_available(self):
        """Calculate remaining available hours"""
        return self.hours_offered - self.hours_allocated
