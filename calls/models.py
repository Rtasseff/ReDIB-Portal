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

    # Resolution (Phase 6)
    is_resolution_locked = models.BooleanField(
        default=False,
        help_text='Prevent resolution changes after finalization (Phase 6)'
    )

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
    def total_approved_hours(self):
        """Calculate total approved hours across all equipment in this call"""
        from applications.models import RequestedAccess
        return RequestedAccess.objects.filter(
            application__call=self,
            application__resolution='accepted'
        ).aggregate(
            total=models.Sum('hours_requested')
        )['total'] or 0


class CallEquipmentAllocation(models.Model):
    """Equipment available per call"""

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

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ['call', 'equipment']
        unique_together = ['call', 'equipment']
        verbose_name = 'Equipment Allocation'

    def __str__(self):
        return f"{self.call.code} - {self.equipment.name}"

    @property
    def total_approved_hours(self):
        """Calculate total approved hours for this equipment in this call"""
        from applications.models import RequestedAccess
        return RequestedAccess.objects.filter(
            equipment=self.equipment,
            application__call=self.call,
            application__resolution='accepted'
        ).aggregate(
            total=models.Sum('hours_requested')
        )['total'] or 0
