"""
Node Resolution service for Phase 6: Node Coordinator Resolution.

Handles the distributed resolution workflow where each node coordinator
independently reviews applications requesting their equipment, then the
system aggregates decisions into a final application-level resolution.

Aggregation Logic:
- ALL nodes accept -> Application accepted
- ANY node rejects -> Application rejected
- No rejects but >=1 waitlist -> Application pending (waitlisted)
"""

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import timedelta


class NodeResolutionService:
    """
    Service for node coordinator resolution workflow and multi-node aggregation.

    Each node coordinator makes an independent decision for their node's equipment,
    which is then aggregated by the system into a final application-level resolution.
    """

    def __init__(self, node=None):
        """
        Initialize service for a specific node.

        Args:
            node: Node instance (for node coordinator views)
        """
        self.node = node

    def get_applications_for_node_resolution(self, call=None):
        """
        Get applications that need resolution from this node.

        Criteria:
        - Application status = 'evaluated'
        - Application requests equipment from this node
        - NodeResolution does not exist yet OR exists but resolution is blank

        Args:
            call: Optional Call instance to filter by call

        Returns:
            QuerySet of Application instances
        """
        from applications.models import Application

        # Get applications with evaluated status
        queryset = Application.objects.filter(
            status='evaluated'
        ).select_related('applicant', 'call').prefetch_related(
            'requested_access__equipment__node',
            'node_resolutions',
            'evaluations__evaluator'
        )

        # Filter by call if provided
        if call:
            queryset = queryset.filter(call=call)

        # Filter: must request equipment from this node
        queryset = queryset.filter(
            requested_access__equipment__node=self.node
        ).distinct()

        # Filter: no existing resolution OR resolution is blank
        # We need to exclude applications where this node has already made a decision
        queryset = queryset.exclude(
            node_resolutions__node=self.node,
            node_resolutions__resolution__in=['accept', 'waitlist', 'reject']
        )

        # Order by final_score descending (highest priority first)
        return queryset.order_by('-final_score', 'code')

    def get_resolved_applications_for_node(self, call=None):
        """
        Get applications that this node has already resolved.

        Args:
            call: Optional Call instance to filter by call

        Returns:
            QuerySet of Application instances
        """
        from applications.models import Application

        queryset = Application.objects.filter(
            node_resolutions__node=self.node,
            node_resolutions__resolution__in=['accept', 'waitlist', 'reject']
        ).select_related('applicant', 'call').prefetch_related(
            'requested_access__equipment__node',
            'node_resolutions'
        ).distinct()

        if call:
            queryset = queryset.filter(call=call)

        return queryset.order_by('-final_score', 'code')

    def get_node_resolution_for_application(self, application):
        """
        Get the NodeResolution for this application and node, if it exists.

        Args:
            application: Application instance

        Returns:
            NodeResolution instance or None
        """
        from applications.models import NodeResolution

        try:
            return NodeResolution.objects.get(
                application=application,
                node=self.node
            )
        except NodeResolution.DoesNotExist:
            return None

    def get_equipment_for_node(self, application):
        """
        Get RequestedAccess items for equipment from this node.

        Args:
            application: Application instance

        Returns:
            QuerySet of RequestedAccess instances
        """
        return application.requested_access.filter(
            equipment__node=self.node
        ).select_related('equipment')

    @transaction.atomic
    def apply_node_resolution(self, application, resolution, comments, approved_hours_dict, user):
        """
        Apply node coordinator's resolution for an application.

        Args:
            application: Application instance
            resolution: str ('accept', 'waitlist', 'reject')
            comments: str (resolution comments)
            approved_hours_dict: dict {equipment_id: hours_approved}
            user: User instance (node coordinator)

        Returns:
            dict with success status and aggregation result

        Raises:
            ValidationError if validation fails
        """
        from applications.models import NodeResolution
        from core.models import UserRole

        # Validate: user must be node coordinator for this node
        if not UserRole.objects.filter(
            user=user,
            role='node_coordinator',
            node=self.node,
            is_active=True
        ).exists():
            raise ValidationError(
                f"User is not an active node coordinator for {self.node.code}"
            )

        # Validate: competitive funding cannot be rejected
        if application.has_competitive_funding and resolution == 'reject':
            raise ValidationError(
                "Applications with competitive funding cannot be rejected. "
                "They must be either accepted or marked as waitlist."
            )

        # Validate: all equipment in approved_hours_dict belongs to this node
        for equipment_id, hours in approved_hours_dict.items():
            try:
                req_access = application.requested_access.get(equipment_id=equipment_id)
                if req_access.equipment.node != self.node:
                    raise ValidationError(
                        f"Equipment {equipment_id} does not belong to {self.node.code}"
                    )
            except application.requested_access.model.DoesNotExist:
                raise ValidationError(
                    f"Equipment {equipment_id} is not requested in this application"
                )

        # Get or create NodeResolution
        node_resolution, created = NodeResolution.objects.get_or_create(
            application=application,
            node=self.node,
            defaults={'reviewer': user}
        )

        # Update resolution
        node_resolution.resolution = resolution
        node_resolution.comments = comments
        node_resolution.reviewed_at = timezone.now()
        node_resolution.reviewer = user
        node_resolution.save()

        # Update hours_approved for equipment at this node
        for equipment_id, hours in approved_hours_dict.items():
            req_access = application.requested_access.get(equipment_id=equipment_id)
            req_access.hours_approved = hours
            req_access.save()

        # Attempt to aggregate resolution (check if all nodes have decided)
        aggregation_result = self.aggregate_application_resolution(application)

        return {
            'success': True,
            'node_resolution': node_resolution.resolution,
            'aggregated': aggregation_result['aggregated'],
            'final_resolution': aggregation_result.get('final_resolution'),
            'details': aggregation_result.get('details', {})
        }

    @transaction.atomic
    def aggregate_application_resolution(self, application):
        """
        Aggregate node resolutions into final application resolution.

        Uses select_for_update() to prevent race conditions when multiple
        nodes are deciding simultaneously.

        Aggregation Logic:
        - ALL nodes accept -> Application.resolution = 'accepted'
        - ANY node rejects -> Application.resolution = 'rejected'
        - No rejects but >=1 waitlist -> Application.resolution = 'pending'
        - Not all nodes decided -> No aggregation, keep status='evaluated'

        Args:
            application: Application instance

        Returns:
            dict: {
                'aggregated': bool,
                'final_resolution': str or None,
                'details': dict
            }
        """
        from applications.models import Application

        # Lock the application row to prevent concurrent aggregation
        application = Application.objects.select_for_update().get(pk=application.pk)

        # Get all nodes that need to provide resolution
        nodes_with_equipment = list(
            application.requested_access.values_list(
                'equipment__node', flat=True
            ).distinct()
        )

        # Get node resolutions that have a decision
        node_resolutions = application.node_resolutions.filter(
            node_id__in=nodes_with_equipment,
            resolution__in=['accept', 'waitlist', 'reject']
        )

        # Check if all nodes have decided
        total_nodes = len(set(nodes_with_equipment))
        decided_nodes = node_resolutions.count()

        if decided_nodes < total_nodes:
            return {
                'aggregated': False,
                'details': {
                    'total_nodes': total_nodes,
                    'decided_nodes': decided_nodes,
                    'reason': 'Not all nodes have made a decision'
                }
            }

        # All nodes have decided - aggregate
        resolutions = list(node_resolutions.values_list('resolution', flat=True))

        # Aggregation logic: reject > waitlist > accept
        if 'reject' in resolutions:
            final_resolution = 'rejected'
            aggregation_reason = f"At least one node rejected (rejections: {resolutions.count('reject')})"
        elif 'waitlist' in resolutions:
            final_resolution = 'pending'
            aggregation_reason = f"No rejections but at least one waitlist (waitlists: {resolutions.count('waitlist')})"
        else:
            final_resolution = 'accepted'
            aggregation_reason = "All nodes accepted"

        # Update application
        application.resolution = final_resolution
        application.resolution_date = timezone.now()

        # Aggregate comments from all nodes
        all_comments = []
        for nr in node_resolutions:
            if nr.comments:
                all_comments.append(f"[{nr.node.code}]: {nr.comments}")
        application.resolution_comments = "\n\n".join(all_comments) if all_comments else ''

        # Update status based on resolution
        if final_resolution == 'accepted':
            application.status = 'accepted'
            # Set acceptance deadline (resolution_date + 10 days)
            application.acceptance_deadline = application.resolution_date + timedelta(days=10)
        elif final_resolution == 'pending':
            application.status = 'pending'
        elif final_resolution == 'rejected':
            application.status = 'rejected'

        application.save()

        # Trigger notification (async if possible)
        self._trigger_resolution_notification(application)

        return {
            'aggregated': True,
            'final_resolution': final_resolution,
            'details': {
                'node_decisions': dict(node_resolutions.values_list('node__code', 'resolution')),
                'aggregation_logic': aggregation_reason,
                'total_nodes': total_nodes
            }
        }

    def _trigger_resolution_notification(self, application):
        """
        Trigger resolution notification to applicant.

        Args:
            application: Application instance with aggregated resolution
        """
        try:
            from applications.tasks import send_single_resolution_notification_task
            send_single_resolution_notification_task.delay(application.id)
        except Exception:
            # Fallback to sync if Celery not available or task doesn't exist
            try:
                from applications.tasks import send_single_resolution_notification_task
                send_single_resolution_notification_task(application.id)
            except Exception:
                # Task may not exist yet - we'll add it later
                pass

    def get_resolution_summary_for_call(self, call):
        """
        Get resolution summary for a call from this node's perspective.

        Args:
            call: Call instance

        Returns:
            dict with resolution statistics
        """
        from applications.models import Application

        # Applications requesting this node's equipment
        apps_requesting_node = Application.objects.filter(
            call=call,
            requested_access__equipment__node=self.node
        ).distinct()

        total = apps_requesting_node.count()
        awaiting = apps_requesting_node.filter(status='evaluated').exclude(
            node_resolutions__node=self.node,
            node_resolutions__resolution__in=['accept', 'waitlist', 'reject']
        ).distinct().count()

        resolved_by_node = apps_requesting_node.filter(
            node_resolutions__node=self.node,
            node_resolutions__resolution__in=['accept', 'waitlist', 'reject']
        ).distinct()

        return {
            'total': total,
            'awaiting_decision': awaiting,
            'resolved_by_this_node': resolved_by_node.count(),
            'node_accepted': apps_requesting_node.filter(
                node_resolutions__node=self.node,
                node_resolutions__resolution='accept'
            ).distinct().count(),
            'node_waitlisted': apps_requesting_node.filter(
                node_resolutions__node=self.node,
                node_resolutions__resolution='waitlist'
            ).distinct().count(),
            'node_rejected': apps_requesting_node.filter(
                node_resolutions__node=self.node,
                node_resolutions__resolution='reject'
            ).distinct().count(),
            # Final application-level resolutions (after aggregation)
            'fully_resolved': apps_requesting_node.filter(
                resolution__in=['accepted', 'pending', 'rejected']
            ).count(),
        }
