"""
Application workflow models for ReDIB COA portal.
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
from simple_history.models import HistoricalRecords
from calls.models import Call
from core.models import Equipment, Node


def signed_pdf_upload_path(instance, filename):
    """
    Generate organized upload path for signed PDFs.
    Format: signed_applications/YYYY/MM/APPLICATION_CODE_signed.pdf
    """
    from django.utils import timezone
    now = timezone.now()
    # Use application code for clear identification
    safe_code = instance.code.replace('-', '_')
    return f'signed_applications/{now.year}/{now.month:02d}/{safe_code}_signed.pdf'


class Application(models.Model):
    """COA application submitted by researcher"""

    APPLICATION_STATUSES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_feasibility_review', 'Under Feasibility Review'),
        ('rejected_feasibility', 'Rejected - Not Feasible'),
        ('pending_evaluation', 'Pending Evaluation'),
        ('under_evaluation', 'Under Evaluation'),
        ('evaluated', 'Evaluated'),
        ('accepted', 'Accepted'),
        ('pending', 'Pending (Waiting List)'),
        ('rejected', 'Rejected'),
        ('declined_by_applicant', 'Declined by Applicant'),  # Phase 7
        ('expired', 'Acceptance Expired'),  # Phase 7
    ]

    PROJECT_TYPES = [
        ('national', 'National'),
        ('international_non_european', 'International, non-European'),
        ('regional', 'Regional'),
        ('european', 'European'),
        ('internal', 'Internal'),
        ('private', 'Private'),
        ('other', 'Other'),
    ]

    # Spanish AEI (Agencia Estatal de Investigación) subject area classification
    SUBJECT_AREAS = [
        ('cso', 'CSO - Social Sciences'),
        ('der', 'DER - Law'),
        ('eco', 'ECO - Economy'),
        ('mlp', 'MLP - Mind, language and thought'),
        ('fla', 'FLA - Culture: Philology, literature and art'),
        ('pha', 'PHA - Studies in history and archaeology'),
        ('edu', 'EDU - Educational Sciences'),
        ('psi', 'PSI - Psychology'),
        ('mtm', 'MTM - Mathematical Sciences'),
        ('fis', 'FIS - Physical Sciences'),
        ('pin', 'PIN - Industrial production, engineering'),
        ('tic', 'TIC - Information and communications technologies'),
        ('eyt', 'EYT - Energy and Transport'),
        ('ctq', 'CTQ - Chemical sciences and technologies'),
        ('mat', 'MAT - Materials Sciences and Technology'),
        ('ctm', 'CTM - Environmental science and technology'),
        ('caa', 'CAA - Agricultural sciences'),
        ('bio', 'BIO - Biosciences and biotechnology'),
        ('bme', 'BME - Biomedicine'),
        ('other', 'Other (specify)'),
    ]

    SERVICE_MODALITIES = [
        ('full_assistance', 'Full Assistance'),
        ('presential', 'Presential'),
        ('self_service', 'Self-Service'),
    ]

    SPECIALIZATION_AREAS = [
        ('clinical', 'Clinical'),
        ('preclinical', 'Preclinical'),
        ('radiotracers', 'Radiotracers and Biomarkers'),
    ]

    RESOLUTIONS = [
        ('', 'Not Resolved'),
        ('accepted', 'Accepted'),
        ('pending', 'Pending (Waiting List)'),
        ('rejected', 'Rejected'),
    ]

    # Basic info
    call = models.ForeignKey(Call, on_delete=models.PROTECT, related_name='applications')
    applicant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='applications')
    code = models.CharField(max_length=30, unique=True, help_text='Auto-generated application code')
    status = models.CharField(max_length=30, choices=APPLICATION_STATUSES, default='draft')
    brief_description = models.CharField(max_length=100, help_text='One-line description')

    # Applicant information (snapshot at submission time)
    applicant_name = models.CharField(max_length=200, blank=True, help_text='Auto-filled from user profile')
    applicant_orcid = models.CharField(max_length=20, blank=True, help_text='Optional ORCID identifier')
    applicant_entity = models.CharField(max_length=200, blank=True, help_text='Institution/organization')
    applicant_email = models.EmailField(blank=True, help_text='Contact email')
    applicant_phone = models.CharField(max_length=30, blank=True, help_text='Contact phone')

    # Funding source
    project_title = models.CharField(max_length=300, blank=True)
    project_code = models.CharField(max_length=100, blank=True)
    funding_agency = models.CharField(max_length=200, blank=True)
    project_type = models.CharField(max_length=50, choices=PROJECT_TYPES, blank=True)
    has_competitive_funding = models.BooleanField(default=False)

    # Classification
    subject_area = models.CharField(max_length=50, choices=SUBJECT_AREAS, blank=True)

    # Service modality
    service_modality = models.CharField(max_length=50, choices=SERVICE_MODALITIES, blank=True)
    specialization_area = models.CharField(max_length=50, choices=SPECIALIZATION_AREAS, blank=True)

    # Scientific content (for evaluation)
    scientific_relevance = models.TextField(
        blank=True,
        help_text='Scientific relevance and originality'
    )
    methodology_description = models.TextField(
        blank=True,
        help_text='Methodology and experimental design'
    )
    expected_contributions = models.TextField(
        blank=True,
        help_text='Expected contributions and results'
    )
    impact_strengths = models.TextField(
        blank=True,
        help_text='Impact and strengths'
    )
    socioeconomic_significance = models.TextField(
        blank=True,
        help_text='Socioeconomic significance'
    )
    opportunity_criteria = models.TextField(
        blank=True,
        help_text='Opportunity criteria and justification'
    )

    # Declarations and compliance
    technical_feasibility_confirmed = models.BooleanField(
        default=False,
        help_text='Confirmed technical feasibility with node'
    )
    uses_animals = models.BooleanField(default=False)
    has_animal_ethics = models.BooleanField(default=False)
    uses_humans = models.BooleanField(default=False)
    has_human_ethics = models.BooleanField(default=False)
    data_consent = models.BooleanField(default=False, help_text='Data processing consent')

    # Signed PDF document tracking
    signed_pdf = models.FileField(
        upload_to=signed_pdf_upload_path,
        null=True,
        blank=True,
        help_text='Uploaded PDF with electronic signature'
    )
    signed_pdf_uploaded_at = models.DateTimeField(null=True, blank=True)
    pdf_generated_at = models.DateTimeField(null=True, blank=True)
    signature_affirmation = models.BooleanField(
        default=False,
        help_text='User affirmed valid electronic signature'
    )

    # Resolution
    final_score = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Average evaluation score'
    )
    resolution = models.CharField(max_length=20, choices=RESOLUTIONS, blank=True)
    resolution_date = models.DateTimeField(null=True, blank=True)
    resolution_comments = models.TextField(blank=True, help_text='Coordinator comments on resolution')

    # Phase 7: Acceptance & Handoff tracking
    accepted_by_applicant = models.BooleanField(
        null=True,
        blank=True,
        help_text='Applicant acceptance: True=accepted, False=declined, None=pending'
    )
    accepted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When applicant accepted or declined'
    )
    acceptance_deadline = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Deadline for applicant to respond (resolution_date + 10 days)'
    )
    handoff_email_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When handoff email was sent to applicant + coordinators'
    )

    # Phase 8: Optional completion tracking
    is_completed = models.BooleanField(
        default=False,
        help_text='Optional: Mark as completed for reporting purposes'
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Optional: When marked as completed'
    )

    # Timestamps
    submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ['-submitted_at', '-created_at']

    def __str__(self):
        return f"{self.code} - {self.brief_description}"

    # Valid state transitions based on design document section 6.1
    # Updated for Phase 7: Simplified acceptance workflow
    VALID_TRANSITIONS = {
        'draft': ['submitted'],
        'submitted': ['under_feasibility_review', 'rejected_feasibility'],
        'under_feasibility_review': ['rejected_feasibility', 'pending_evaluation'],
        'rejected_feasibility': [],  # Terminal state
        'pending_evaluation': ['under_evaluation'],
        'under_evaluation': ['evaluated'],
        'evaluated': ['accepted', 'pending', 'rejected'],
        'accepted': ['declined_by_applicant', 'expired'],  # Phase 7: Applicant can decline or expire
        'pending': ['accepted', 'rejected'],  # Can be promoted from waiting list
        'rejected': [],  # Terminal state
        'declined_by_applicant': [],  # Terminal state - Phase 7
        'expired': [],  # Terminal state - Phase 7
    }

    def save(self, *args, **kwargs):
        """Generate application code and validate state transitions"""
        from django.db import IntegrityError

        # Generate application code if not exists
        if not self.code:
            # Generate code like: CALL-CODE-001
            # Find the highest number used across all applications for this call
            # (both draft codes like CALL-001 and submitted codes like CALL-APP-001)
            max_retries = 5
            for attempt in range(max_retries):
                all_apps = Application.objects.filter(call=self.call)

                max_num = 0
                for app in all_apps:
                    if app.code:
                        try:
                            # Extract the last numeric part from codes like:
                            # "CALL-001" or "CALL-APP-001"
                            parts = app.code.split('-')
                            last_part = parts[-1]
                            num = int(last_part)
                            max_num = max(max_num, num)
                        except (ValueError, IndexError):
                            # Skip codes that don't end with a number
                            continue

                new_num = max_num + 1
                self.code = f"{self.call.code}-{new_num:03d}"

                # Validate state transition if updating existing application
                if self.pk:
                    old_status = Application.objects.get(pk=self.pk).status
                    if old_status != self.status:
                        valid_next_states = self.VALID_TRANSITIONS.get(old_status, [])
                        if self.status not in valid_next_states:
                            from django.core.exceptions import ValidationError
                            raise ValidationError(
                                f"Invalid status transition from '{old_status}' to '{self.status}'. "
                                f"Valid next states: {', '.join(valid_next_states) if valid_next_states else 'None (terminal state)'}"
                            )

                try:
                    super().save(*args, **kwargs)
                    return  # Success, exit
                except IntegrityError as e:
                    # If UNIQUE constraint failed on code, retry with next number
                    if 'applications_application.code' in str(e) or 'UNIQUE constraint' in str(e):
                        if attempt < max_retries - 1:
                            # Clear the code to force regeneration
                            self.code = None
                            continue
                        else:
                            # Final attempt failed, re-raise
                            raise
                    else:
                        # Different IntegrityError, re-raise
                        raise
        else:
            # Code already exists, just validate and save
            if self.pk:
                old_status = Application.objects.get(pk=self.pk).status
                if old_status != self.status:
                    valid_next_states = self.VALID_TRANSITIONS.get(old_status, [])
                    if self.status not in valid_next_states:
                        from django.core.exceptions import ValidationError
                        raise ValidationError(
                            f"Invalid status transition from '{old_status}' to '{self.status}'. "
                            f"Valid next states: {', '.join(valid_next_states) if valid_next_states else 'None (terminal state)'}"
                        )

            super().save(*args, **kwargs)

    def can_transition_to(self, new_status):
        """
        Check if application can transition to a new status.

        Args:
            new_status: The target status to check

        Returns:
            Boolean indicating if transition is valid
        """
        valid_next_states = self.VALID_TRANSITIONS.get(self.status, [])
        return new_status in valid_next_states

    # Phase 7: Acceptance deadline helper methods
    @property
    def acceptance_deadline_passed(self):
        """
        Check if acceptance deadline has passed.

        Returns:
            Boolean indicating if deadline has passed
        """
        if not self.acceptance_deadline:
            return False
        from django.utils import timezone
        return timezone.now() > self.acceptance_deadline

    @property
    def days_until_acceptance_deadline(self):
        """
        Calculate days remaining until acceptance deadline.

        Returns:
            Integer days remaining, or None if no deadline set
        """
        if not self.acceptance_deadline:
            return None
        from django.utils import timezone
        delta = self.acceptance_deadline - timezone.now()
        return delta.days

    def calculate_acceptance_deadline(self):
        """
        Calculate acceptance deadline (resolution_date + 10 days).

        Per REDIB-02-PDA section 6.1.6: "Applicants have a period of ten (10) days
        from the publication of the resolution to accept or reject in writing
        the access granted"

        Returns:
            DateTime object representing the deadline, or None if no resolution_date
        """
        if self.resolution_date:
            from datetime import timedelta
            return self.resolution_date + timedelta(days=10)
        return None

    def get_next_valid_states(self):
        """
        Get list of valid next states for this application.

        Returns:
            List of valid status choices
        """
        return self.VALID_TRANSITIONS.get(self.status, [])

    @property
    def total_hours_requested(self):
        """Calculate total hours requested across all equipment"""
        return self.requested_access.aggregate(
            total=models.Sum('hours_requested')
        )['total'] or 0


class RequestedAccess(models.Model):
    """Equipment access requests within an application"""

    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='requested_access'
    )
    equipment = models.ForeignKey(
        Equipment,
        on_delete=models.PROTECT,
        related_name='access_requests'
    )
    hours_requested = models.DecimalField(
        max_digits=6,
        decimal_places=1,
        validators=[MinValueValidator(0)],
        help_text='Hours requested by applicant'
    )
    hours_approved = models.DecimalField(
        max_digits=6,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text='Hours approved/granted (same as requested for Phase 7 simplification)'
    )
    actual_hours_used = models.DecimalField(
        max_digits=6,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text='Actual hours used (reported on completion)'
    )

    # Equipment completion tracking
    is_completed = models.BooleanField(
        default=False,
        help_text='Equipment access marked as completed (by either applicant or node coordinator)'
    )
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='completed_equipment_requests',
        help_text='User who marked this equipment access as completed'
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When this equipment access was marked as completed'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ['application', 'equipment']
        unique_together = ['application', 'equipment']
        verbose_name = 'Requested Access'
        verbose_name_plural = 'Requested Accesses'

    def __str__(self):
        return f"{self.application.code} - {self.equipment.name}: {self.hours_requested}h"

    def save(self, *args, **kwargs):
        """Auto-populate hours_approved from hours_requested if accepted"""
        if self.hours_approved is None and self.application.status == 'accepted':
            self.hours_approved = self.hours_requested
        super().save(*args, **kwargs)


class FeasibilityReview(models.Model):
    """Node technical feasibility assessment"""

    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='feasibility_reviews'
    )
    node = models.ForeignKey(Node, on_delete=models.PROTECT)
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='feasibility_reviews_conducted'
    )

    is_feasible = models.BooleanField(null=True, blank=True)
    comments = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ['application', 'node']
        unique_together = ['application', 'node']

    def __str__(self):
        status = 'Pending'
        if self.is_feasible is True:
            status = 'Feasible'
        elif self.is_feasible is False:
            status = 'Not Feasible'
        return f"{self.application.code} - {self.node.code}: {status}"


class NodeResolution(models.Model):
    """
    Node coordinator's resolution decision for applications requesting their equipment.

    Each node coordinator makes an independent decision for their node's equipment,
    which is then aggregated by the system into a final application-level resolution.

    Aggregation Logic:
    - ALL nodes accept → Application accepted
    - ANY node rejects → Application rejected
    - No rejects but ≥1 waitlist → Application pending (waitlisted)
    """

    NODE_RESOLUTION_CHOICES = [
        ('', 'Not Decided'),
        ('accept', 'Accept'),
        ('waitlist', 'Waitlist'),
        ('reject', 'Reject'),
    ]

    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='node_resolutions'
    )
    node = models.ForeignKey(
        Node,
        on_delete=models.PROTECT,
        help_text='Node providing this resolution'
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='node_resolutions_conducted',
        help_text='Node coordinator who made this decision'
    )

    resolution = models.CharField(
        max_length=20,
        choices=NODE_RESOLUTION_CHOICES,
        blank=True,
        help_text="This node's resolution decision"
    )
    comments = models.TextField(
        blank=True,
        help_text='Node coordinator comments on resolution'
    )
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When node coordinator made their decision'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ['application', 'node']
        unique_together = ['application', 'node']
        verbose_name = 'Node Resolution'
        verbose_name_plural = 'Node Resolutions'

    def __str__(self):
        status = self.get_resolution_display() if self.resolution else 'Pending'
        return f"{self.application.code} - {self.node.code}: {status}"
