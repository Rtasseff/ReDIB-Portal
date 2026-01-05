"""
Utility functions for evaluations app - Phase 5
"""

from django.db.models import Avg
from django.utils import timezone


def check_and_transition_application(application):
    """
    Check if all evaluations for an application are complete.
    If complete, transition application status and notify coordinator.

    Args:
        application: Application instance to check

    Returns:
        dict with status information
    """
    total_evaluations = application.evaluations.count()
    completed_evaluations = application.evaluations.filter(
        completed_at__isnull=False
    ).count()

    result = {
        'total': total_evaluations,
        'completed': completed_evaluations,
        'all_complete': False,
        'transitioned': False,
        'average_score': None
    }

    # Check if we have evaluations and all are complete
    if total_evaluations == 0:
        return result

    all_complete = (completed_evaluations == total_evaluations)
    result['all_complete'] = all_complete

    if all_complete:
        # Calculate average score
        avg_result = application.evaluations.aggregate(avg=Avg('total_score'))
        average_score = avg_result['avg']
        result['average_score'] = average_score

        # Save final score to application
        application.final_score = average_score

        # Transition state if currently under_evaluation
        if application.status == 'under_evaluation':
            application.status = 'evaluated'

        application.save()

        if application.status == 'evaluated':
            result['transitioned'] = True

            # Trigger notification to coordinator (async)
            from evaluations.tasks import notify_coordinator_evaluations_complete
            try:
                notify_coordinator_evaluations_complete.delay(
                    application_id=application.id,
                    average_score=float(average_score) if average_score else 0.0
                )
            except Exception as e:
                # If Celery/Redis not available (e.g., testing), call synchronously
                notify_coordinator_evaluations_complete(
                    application_id=application.id,
                    average_score=float(average_score) if average_score else 0.0
                )

    return result


def get_blind_application_data(application):
    """
    Return application data with applicant identity hidden for blind evaluation.

    This ensures evaluators cannot see:
    - Applicant name
    - Applicant organization/entity
    - Applicant contact information (email, phone)
    - Applicant ORCID

    Args:
        application: Application instance

    Returns:
        dict with safe, non-identifying application data
    """
    return {
        # Basic info (non-identifying)
        'id': application.id,
        'code': application.code,
        'brief_description': application.brief_description,
        'call': application.call,

        # Scientific content (fully visible for evaluation)
        'scientific_relevance': application.scientific_relevance,
        'methodology_description': application.methodology_description,
        'expected_contributions': application.expected_contributions,
        'impact_strengths': application.impact_strengths,
        'socioeconomic_significance': application.socioeconomic_significance,
        'opportunity_criteria': application.opportunity_criteria,

        # Project classification (non-identifying)
        'project_type': application.get_project_type_display() if application.project_type else 'Not specified',
        'subject_area': application.get_subject_area_display() if application.subject_area else 'Not specified',
        'specialization_area': application.get_specialization_area_display() if application.specialization_area else 'Not specified',
        'service_modality': application.get_service_modality_display() if application.service_modality else 'Not specified',
        'has_competitive_funding': application.has_competitive_funding,

        # Equipment requests
        'requested_access': application.requested_access.all().select_related('equipment', 'equipment__node'),

        # Research ethics info (non-identifying)
        'uses_animals': application.uses_animals,
        'has_animal_ethics': application.has_animal_ethics,
        'uses_humans': application.uses_humans,
        'has_human_ethics': application.has_human_ethics,

        # IMPORTANT: The following fields are HIDDEN for blind evaluation:
        # - applicant (User object)
        # - applicant_name
        # - applicant_entity
        # - applicant_email
        # - applicant_phone
        # - applicant_orcid
        # - project_title (may contain identifying information)
        # - project_code
        # - funding_agency
    }


def is_evaluation_locked(evaluation):
    """
    Check if an evaluation is locked and cannot be edited.

    An evaluation is locked if:
    1. It has been completed (completed_at is set), OR
    2. The evaluation deadline has passed

    Args:
        evaluation: Evaluation instance

    Returns:
        tuple: (is_locked, reason)
    """
    now = timezone.now()

    # Check if completed
    if evaluation.is_complete:
        return (True, 'completed')

    # Check if past deadline
    deadline = evaluation.application.call.evaluation_deadline
    if deadline and deadline < now:
        return (True, 'past_deadline')

    return (False, None)


def get_evaluation_progress_for_application(application):
    """
    Get evaluation progress statistics for an application.

    Args:
        application: Application instance

    Returns:
        dict with progress information
    """
    evaluations = application.evaluations.all()
    total = evaluations.count()
    completed = evaluations.filter(completed_at__isnull=False).count()
    pending = total - completed

    progress_percentage = (completed / total * 100) if total > 0 else 0

    return {
        'total': total,
        'completed': completed,
        'pending': pending,
        'progress_percentage': round(progress_percentage, 1),
        'all_complete': (total > 0 and completed == total)
    }
