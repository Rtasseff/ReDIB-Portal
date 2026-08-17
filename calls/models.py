"""
Call management models for ReDIB COA portal.
"""

import hashlib

from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator
from simple_history.models import HistoricalRecords
from core.models import Equipment


class Call(models.Model):
    """COA Call periods"""

    CALL_STATUSES = [
        ('draft', 'Draft'),
        ('announced', 'Announced - Opens Soon'),
        ('open', 'Open for Submissions'),
        ('closed', 'Closed - Under Evaluation'),
        ('resolved', 'Resolved'),
    ]

    # Statuses whose calls are visible on the public site. `draft` is not
    # public; `announced` is advertised but takes no applications.
    PUBLIC_STATUSES = ['announced', 'open', 'closed', 'resolved']

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
    def is_announced(self):
        """Call is advertised publicly but not yet accepting submissions."""
        return self.status == 'announced'

    @property
    def is_publicly_visible(self):
        """Call appears on the public calls pages."""
        return self.status in self.PUBLIC_STATUSES

    @property
    def accepts_consult_requests(self):
        """Anyone can ask a node for a consult while a call is announced or
        open. Once submissions close there is nothing left to consult about."""
        return self.status in ['announced', 'open']

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


class ConsultRequest(models.Model):
    """An informal request for a consult about specific equipment on a call.

    Submitted from the public call page by anyone (login not required) while
    the call is announced or open. Routed by email to every active node
    coordinator of each node whose equipment was selected. This is contact
    only: it starts no application and no feasibility review.
    """

    call = models.ForeignKey(
        Call,
        on_delete=models.CASCADE,
        related_name='consult_requests'
    )
    equipment = models.ManyToManyField(
        Equipment,
        related_name='consult_requests',
        help_text='Equipment on this call the requester asked about'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='consult_requests',
        help_text='Set when the requester was logged in; anonymous otherwise'
    )

    # Contact details as typed on the form (never overwritten from the profile,
    # so the row stays a faithful record of what was submitted).
    name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    organization = models.CharField(max_length=255, blank=True)
    message = models.TextField(blank=True, max_length=2000)

    created_at = models.DateTimeField(auto_now_add=True)
    emails_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the coordinator notifications were dispatched'
    )
    ip_hash = models.CharField(
        max_length=64,
        blank=True,
        help_text='SHA-256 of the submitting IP, for abuse follow-up only'
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Consult Request'

    def __str__(self):
        return f"{self.call.code} - {self.name} ({self.created_at:%Y-%m-%d})"

    @staticmethod
    def hash_ip(ip_address):
        """One-way hash of a client IP. Returns '' for a missing address."""
        if not ip_address:
            return ''
        return hashlib.sha256(ip_address.encode('utf-8')).hexdigest()

    def equipment_by_node(self):
        """Requested equipment grouped as {node: [equipment, ...]}."""
        grouped = {}
        for item in self.equipment.select_related('node__organization').order_by(
            'node__code', 'name'
        ):
            grouped.setdefault(item.node, []).append(item)
        return grouped
