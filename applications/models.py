"""
Application workflow models for ReDIB COA portal.
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
from simple_history.models import HistoricalRecords
from calls.models import Call
from core.models import Equipment, Node


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
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]

    PROJECT_TYPES = [
        ('national_public', 'National Public Competitive Project'),
        ('international', 'International Project'),
        ('regional', 'Regional Project'),
        ('private', 'Private Funding'),
        ('other', 'Other'),
    ]

    # Spanish AEI (Agencia Estatal de Investigación) subject area classification
    SUBJECT_AREAS = [
        ('phy', 'PHY - Physics'),
        ('che', 'CHE - Chemistry'),
        ('mat', 'MAT - Materials Science and Technology'),
        ('ear', 'EAR - Earth Sciences'),
        ('bio', 'BIO - Biology'),
        ('med', 'MED - Medicine'),
        ('agr', 'AGR - Agricultural Sciences'),
        ('eng', 'ENG - Engineering and Architecture'),
        ('soc', 'SOC - Social Sciences'),
        ('eco', 'ECO - Economics'),
        ('law', 'LAW - Law'),
        ('hum', 'HUM - Humanities'),
        ('other', 'Other'),
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
    VALID_TRANSITIONS = {
        'draft': ['submitted'],
        'submitted': ['under_feasibility_review', 'rejected_feasibility'],
        'under_feasibility_review': ['rejected_feasibility', 'pending_evaluation'],
        'rejected_feasibility': [],  # Terminal state
        'pending_evaluation': ['under_evaluation'],
        'under_evaluation': ['evaluated'],
        'evaluated': ['accepted', 'pending', 'rejected'],
        'accepted': ['scheduled'],
        'pending': ['scheduled', 'rejected'],
        'rejected': [],  # Terminal state
        'scheduled': ['in_progress'],
        'in_progress': ['completed'],
        'completed': [],  # Terminal state
    }

    def save(self, *args, **kwargs):
        """Generate application code and validate state transitions"""
        # Generate application code if not exists
        if not self.code:
            # Generate code like: CALL-CODE-001
            last_app = Application.objects.filter(
                call=self.call
            ).order_by('-code').first()

            if last_app and last_app.code:
                try:
                    last_num = int(last_app.code.split('-')[-1])
                    new_num = last_num + 1
                except (ValueError, IndexError):
                    new_num = 1
            else:
                new_num = 1

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
        validators=[MinValueValidator(0)]
    )

    created_at = models.DateTimeField(auto_now_add=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ['application', 'equipment']
        unique_together = ['application', 'equipment']
        verbose_name = 'Requested Access'
        verbose_name_plural = 'Requested Accesses'

    def __str__(self):
        return f"{self.application.code} - {self.equipment.name}: {self.hours_requested}h"


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
