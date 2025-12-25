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

    # Scoring (1-5 scale per criteria)
    score_relevance = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text='Scientific relevance and originality (1-5)'
    )
    score_methodology = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text='Methodology and experimental design (1-5)'
    )
    score_contributions = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text='Expected contributions and results (1-5)'
    )
    score_impact = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text='Impact and strengths (1-5)'
    )
    score_opportunity = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text='Opportunity criteria (1-5)'
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
            self.score_relevance,
            self.score_methodology,
            self.score_contributions,
            self.score_impact,
            self.score_opportunity
        ]

        # Calculate total only if all scores are provided
        if all(score is not None for score in scores):
            self.total_score = sum(scores) / len(scores)

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
