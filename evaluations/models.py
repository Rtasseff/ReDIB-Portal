"""
Evaluation models for ReDIB COA portal.
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
from simple_history.models import HistoricalRecords
from applications.models import Application


class Evaluation(models.Model):
    """Evaluator assessment of application"""

    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='evaluations'
    )
    evaluator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='evaluations_conducted'
    )

    # Category 1: Scientific and Technical Relevance (0-2 scale)
    score_quality_originality = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(2)],
        help_text='Quality and originality of the project and research plan (0-2)'
    )
    score_methodology_design = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(2)],
        help_text='Suitability of methodology, design, and work plan to the objectives (0-2)'
    )
    score_expected_contributions = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(2)],
        help_text='Expected scientific–technical contributions arising from the proposal (0-2)'
    )

    # Category 2: Timeliness and Impact (0-2 scale)
    score_knowledge_advancement = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(2)],
        help_text='Contribution of the research to the advancement of knowledge (0-2)'
    )
    score_social_economic_impact = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(2)],
        help_text='Potential social, economic and/or industrial impact of the expected results (0-2)'
    )
    score_exploitation_dissemination = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(2)],
        help_text='Opportunity for exploitation, translation and/or dissemination (0-2)'
    )

    # Recommendation
    RECOMMENDATION_CHOICES = [
        ('approved', 'Approved'),
        ('denied', 'Denied'),
    ]
    recommendation = models.CharField(
        max_length=20,
        choices=RECOMMENDATION_CHOICES,
        null=True,
        blank=True,
        help_text='Accept or reject recommendation'
    )

    total_score = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Computed total score'
    )

    comments = models.TextField(blank=True, help_text='Evaluator comments')

    assigned_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ['application', 'evaluator']
        unique_together = ['application', 'evaluator']

    def __str__(self):
        status = 'Pending'
        if self.completed_at:
            status = f'Completed ({self.total_score})'
        return f"{self.application.code} - {self.evaluator.email}: {status}"

    def save(self, *args, **kwargs):
        """Calculate total score before saving"""
        scores = [
            self.score_quality_originality,
            self.score_methodology_design,
            self.score_expected_contributions,
            self.score_knowledge_advancement,
            self.score_social_economic_impact,
            self.score_exploitation_dissemination
        ]

        # Calculate total only if all scores are provided
        # Total score is the SUM of all 6 scores (max 12), not average
        if all(score is not None for score in scores):
            self.total_score = sum(scores)

            # Set completed_at if not already set and all scores are complete
            if not self.completed_at:
                from django.utils import timezone
                self.completed_at = timezone.now()
        else:
            self.total_score = None

        super().save(*args, **kwargs)

    @property
    def is_complete(self):
        """Check if evaluation is complete"""
        return self.completed_at is not None
