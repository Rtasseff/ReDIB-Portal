"""
Resolution service for Phase 6: Resolution & Prioritization.

Handles coordinator workflow to review evaluated applications, apply regulatory
auto-approval rules, allocate limited equipment hours, and trigger notifications.
"""

from django.db import transaction
from django.db.models import Sum, Avg, Count, Q
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal


class ResolutionService:
    """Centralized resolution business logic for coordinator workflow"""

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

    def calculate_hours_availability(self):
        """
        Calculate hours availability per equipment type.

        Returns:
            dict: {equipment_id: {
                'equipment': Equipment instance,
                'offered': Decimal (hours from CallEquipmentAllocation),
                'allocated': Decimal (sum of hours_granted),
                'remaining': Decimal (offered - allocated),
                'over_allocated': bool (True if allocated > offered)
            }}
        """
        from applications.models import RequestedAccess
        from core.models import Equipment

        # Get hours offered per equipment for this call
        hours_offered = {}
        for allocation in self.call.equipment_allocations.select_related('equipment'):
            hours_offered[allocation.equipment.id] = {
                'equipment': allocation.equipment,
                'offered': allocation.hours_offered,
                'allocated': Decimal('0.0'),
                'remaining': allocation.hours_offered,
                'over_allocated': False
            }

        # Calculate hours already allocated (hours_granted)
        hours_allocated = (
            RequestedAccess.objects
            .filter(
                application__call=self.call,
                application__resolution__in=['accepted', 'pending'],
                hours_granted__isnull=False
            )
            .values('equipment')
            .annotate(total=Sum('hours_granted'))
        )

        # Update allocated and remaining hours
        for item in hours_allocated:
            equipment_id = item['equipment']
            if equipment_id in hours_offered:
                allocated = item['total'] or Decimal('0.0')
                hours_offered[equipment_id]['allocated'] = allocated
                hours_offered[equipment_id]['remaining'] = (
                    hours_offered[equipment_id]['offered'] - allocated
                )
                hours_offered[equipment_id]['over_allocated'] = (
                    allocated > hours_offered[equipment_id]['offered']
                )

        return hours_offered

    def can_accept_application(self, application):
        """
        Check if application can be accepted based on hours availability.

        Auto-Approval Rule (CRITICAL):
        Applications with has_competitive_funding=True can ALWAYS be accepted,
        even if hours are exhausted (over-allocation allowed).

        Args:
            application: Application instance

        Returns:
            tuple: (can_accept: bool, reason: str, details: dict)
        """
        # Auto-approve competitive funding applications
        if application.has_competitive_funding:
            return (True, 'auto_approved_competitive_funding', {
                'message': 'Auto-approved (competitive funding)'
            })

        # Check hours availability for each equipment request
        hours_availability = self.calculate_hours_availability()
        can_accept = True
        insufficient_hours = []

        for requested_access in application.requested_access.select_related('equipment'):
            equipment_id = requested_access.equipment.id
            hours_requested = requested_access.hours_requested

            if equipment_id not in hours_availability:
                can_accept = False
                insufficient_hours.append({
                    'equipment': requested_access.equipment.name,
                    'requested': hours_requested,
                    'available': Decimal('0.0'),
                    'reason': 'Equipment not in call allocation'
                })
                continue

            hours_remaining = hours_availability[equipment_id]['remaining']

            if hours_requested > hours_remaining:
                can_accept = False
                insufficient_hours.append({
                    'equipment': requested_access.equipment.name,
                    'requested': hours_requested,
                    'available': hours_remaining,
                    'reason': 'Insufficient hours remaining'
                })

        if can_accept:
            return (True, 'hours_available', {'message': 'Sufficient hours available'})
        else:
            return (False, 'insufficient_hours', {
                'message': 'Insufficient hours for one or more equipment types',
                'details': insufficient_hours
            })

    @transaction.atomic
    def apply_resolution(self, application, resolution, comments='', user=None):
        """
        Apply resolution to a single application (atomic transaction).

        Business Rules:
        1. Competitive funding apps CANNOT be rejected (validation error)
        2. Hours must be available for acceptance (unless competitive funding)
        3. Resolution sets: resolution, resolution_date, resolution_comments, status
        4. Hours_granted set for each RequestedAccess

        Args:
            application: Application instance
            resolution: str ('accepted', 'pending', 'rejected')
            comments: str (optional resolution comments)
            user: User instance (coordinator)

        Returns:
            dict with success status and details

        Raises:
            ValidationError if validation fails
        """
        # Validate: competitive funding cannot be rejected
        if application.has_competitive_funding and resolution == 'rejected':
            raise ValidationError(
                "Applications with competitive funding cannot be rejected. "
                "They must be either accepted or marked as pending."
            )

        # Validate: hours availability for acceptance (unless competitive funding)
        if resolution in ['accepted', 'pending']:
            can_accept, reason, details = self.can_accept_application(application)
            if resolution == 'accepted' and not can_accept and not application.has_competitive_funding:
                raise ValidationError(
                    f"Cannot accept application: {details['message']}. "
                    f"Consider marking as 'pending' instead."
                )

        # Update resolution fields
        application.resolution = resolution
        application.resolution_date = timezone.now()
        application.resolution_comments = comments

        # Update status based on resolution
        if resolution == 'accepted':
            application.status = 'accepted'
        elif resolution == 'pending':
            application.status = 'pending'
        elif resolution == 'rejected':
            application.status = 'rejected'

        # Set hours_granted for accepted/pending applications
        if resolution in ['accepted', 'pending']:
            for requested_access in application.requested_access.all():
                requested_access.hours_granted = requested_access.hours_requested
                requested_access.save()
        else:
            # Rejected applications get no hours
            for requested_access in application.requested_access.all():
                requested_access.hours_granted = None
                requested_access.save()

        application.save()

        return {
            'success': True,
            'application_id': application.id,
            'application_code': application.code,
            'resolution': resolution,
            'status': application.status,
            'hours_granted': application.requested_access.aggregate(
                total=Sum('hours_granted')
            )['total'] or Decimal('0.0')
        }

    @transaction.atomic
    def bulk_auto_allocate(self, threshold_score=3.0, auto_pending=True):
        """
        Auto-allocate applications by priority until hours exhausted.

        Allocation Logic:
        1. Get prioritized applications (score DESC, code ASC)
        2. For each application:
           - If has_competitive_funding: ACCEPT (even if hours exhausted)
           - Elif score >= threshold AND hours available: ACCEPT
           - Elif score >= threshold AND hours exhausted: PENDING (if auto_pending)
           - Else: REJECT

        Args:
            threshold_score: Decimal (minimum score for acceptance, default 3.0)
            auto_pending: bool (auto-set to pending when hours exhausted, default True)

        Returns:
            dict with allocation summary
        """
        threshold_score = Decimal(str(threshold_score))
        applications = self.get_prioritized_applications()

        results = {
            'total': applications.count(),
            'accepted': 0,
            'pending': 0,
            'rejected': 0,
            'details': []
        }

        for application in applications:
            # Auto-approve competitive funding
            if application.has_competitive_funding:
                result = self.apply_resolution(application, 'accepted',
                    comments='Auto-approved (competitive funding)')
                results['accepted'] += 1
                results['details'].append({
                    'application_code': application.code,
                    'resolution': 'accepted',
                    'reason': 'Auto-approved (competitive funding)',
                    'score': application.final_score
                })
                continue

            # Check score threshold
            if application.final_score < threshold_score:
                result = self.apply_resolution(application, 'rejected',
                    comments=f'Score below threshold ({threshold_score})')
                results['rejected'] += 1
                results['details'].append({
                    'application_code': application.code,
                    'resolution': 'rejected',
                    'reason': f'Score below threshold ({threshold_score})',
                    'score': application.final_score
                })
                continue

            # Check hours availability
            can_accept, reason, details = self.can_accept_application(application)

            if can_accept:
                result = self.apply_resolution(application, 'accepted',
                    comments=f'Auto-allocated (score: {application.final_score})')
                results['accepted'] += 1
                results['details'].append({
                    'application_code': application.code,
                    'resolution': 'accepted',
                    'reason': 'Hours available',
                    'score': application.final_score
                })
            else:
                # Hours exhausted
                if auto_pending:
                    result = self.apply_resolution(application, 'pending',
                        comments=f'Pending (hours exhausted, score: {application.final_score})')
                    results['pending'] += 1
                    results['details'].append({
                        'application_code': application.code,
                        'resolution': 'pending',
                        'reason': 'Hours exhausted',
                        'score': application.final_score
                    })
                else:
                    result = self.apply_resolution(application, 'rejected',
                        comments=f'Rejected (hours exhausted, score: {application.final_score})')
                    results['rejected'] += 1
                    results['details'].append({
                        'application_code': application.code,
                        'resolution': 'rejected',
                        'reason': 'Hours exhausted',
                        'score': application.final_score
                    })

        return results

    @transaction.atomic
    def finalize_resolution(self, user):
        """
        Finalize call resolution and trigger notifications.

        Validation:
        - All evaluated applications must have a resolution set
        - Call must not already be locked

        Actions:
        - Lock call (is_resolution_locked = True)
        - Trigger notification task (async via Celery)

        Args:
            user: User instance (coordinator)

        Returns:
            dict with finalization status

        Raises:
            ValidationError if validation fails
        """
        # Check if already locked
        if self.call.is_resolution_locked:
            raise ValidationError("Call resolution is already finalized and locked.")

        # Validate: all evaluated apps have resolution
        evaluated_apps = self.call.applications.filter(status='evaluated')
        if evaluated_apps.exists():
            raise ValidationError(
                f"Cannot finalize: {evaluated_apps.count()} application(s) "
                f"still in 'evaluated' status. All applications must have a resolution."
            )

        # Get statistics
        resolved_apps = self.call.applications.filter(
            resolution__in=['accepted', 'pending', 'rejected']
        )
        stats = {
            'total': resolved_apps.count(),
            'accepted': resolved_apps.filter(resolution='accepted').count(),
            'pending': resolved_apps.filter(resolution='pending').count(),
            'rejected': resolved_apps.filter(resolution='rejected').count(),
        }

        # Phase 7: Set acceptance deadline for accepted applications
        # Per REDIB-02-PDA section 6.1.6: "10 days to accept or reject"
        from datetime import timedelta
        for application in resolved_apps.filter(resolution='accepted'):
            if not application.acceptance_deadline and application.resolution_date:
                application.acceptance_deadline = application.resolution_date + timedelta(days=10)
                application.save()

        # Lock call
        self.call.is_resolution_locked = True
        self.call.save()

        # Trigger notification task (async)
        try:
            from applications.tasks import send_resolution_notifications_task
            send_resolution_notifications_task.delay(self.call.id)
        except Exception as e:
            # Fallback to synchronous if Celery/Redis not available
            from applications.tasks import send_resolution_notifications_task
            send_resolution_notifications_task(self.call.id)

        return {
            'success': True,
            'call_id': self.call.id,
            'call_code': self.call.code,
            'finalized_at': timezone.now(),
            'statistics': stats
        }

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
