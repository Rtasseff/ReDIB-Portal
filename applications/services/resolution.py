"""
Read-only resolution summaries for the ReDIB coordinator's Resolution page.

The nodes make the decisions (NodeResolutionService). This service only
ranks a call's applications and counts where they stand; it writes nothing.
The old coordinator-side Decide / Bulk / Finalize actions were removed (#84).
"""

from django.db.models import Avg


class ResolutionService:
    """Ranking and progress counts for one call's resolution (read-only)."""

    def __init__(self, call):
        """
        Initialize resolution service for a call.

        Args:
            call: Call instance
        """
        self.call = call

    def get_prioritized_applications(self):
        """
        Get evaluated applications sorted by priority rules.

        Sorting:
        - PRIMARY: final_score DESC (highest first)
        - SECONDARY: code ASC (alphabetical for ties)

        Returns:
            QuerySet of Application instances
        """
        from applications.models import Application

        return (
            Application.objects
            .filter(call=self.call, status='evaluated')
            .select_related('applicant', 'call')
            .prefetch_related(
                'requested_access__equipment__node',
                'evaluations__evaluator'
            )
            .order_by('-final_score', 'code')
        )

    def get_resolution_summary(self):
        """
        Get summary of resolution progress for a call.

        Returns:
            dict with resolution statistics
        """
        applications = self.call.applications.all()

        stats = {
            'total': applications.count(),
            'evaluated': applications.filter(status='evaluated').count(),
            'accepted': applications.filter(resolution='accepted').count(),
            'pending': applications.filter(resolution='pending').count(),
            'rejected': applications.filter(resolution='rejected').count(),
            'competitive_funding': applications.filter(has_competitive_funding=True).count(),
            'average_score': applications.filter(
                final_score__isnull=False
            ).aggregate(avg=Avg('final_score'))['avg'],
            'is_locked': self.call.is_resolution_locked,
            'all_resolved': applications.filter(status='evaluated').count() == 0
        }

        return stats
