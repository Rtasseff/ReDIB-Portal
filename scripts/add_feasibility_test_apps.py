#!/usr/bin/env python
"""
Quick script to add applications under feasibility review for CIC and CNIC nodes.
Run with: python add_feasibility_test_apps.py
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'redib.settings')
django.setup()

from django.utils import timezone
from django.contrib.auth import get_user_model
from applications.models import Application, RequestedAccess, FeasibilityReview
from calls.models import Call
from core.models import Equipment, Node, UserRole

User = get_user_model()

def create_feasibility_test_apps():
    """Create 2 applications under feasibility review for CIC and CNIC nodes."""

    # Get the open call
    call = Call.objects.filter(status='open').first()
    if not call:
        print("ERROR: No open call found!")
        return

    # Get test applicants
    applicants = list(User.objects.filter(email__icontains='testapplicant'))
    if not applicants:
        print("ERROR: No test applicants found! Run seed_test_applicants first.")
        return

    # Get nodes
    cic_node = Node.objects.filter(code__icontains='CIC').first()
    cnic_node = Node.objects.filter(code__icontains='CNIC').exclude(code='CNIC').first()  # Get TRIMA-CNIC

    if not cic_node or not cnic_node:
        print(f"ERROR: Could not find CIC or CNIC nodes!")
        print(f"Available nodes: {list(Node.objects.values_list('code', flat=True))}")
        return

    # Get equipment
    cic_equipment = Equipment.objects.filter(node=cic_node, is_active=True).first()
    cnic_equipment = Equipment.objects.filter(node=cnic_node, is_active=True).first()

    if not cic_equipment or not cnic_equipment:
        print("ERROR: No equipment found for these nodes!")
        return

    # Get node coordinators
    cic_coord = UserRole.objects.filter(
        role='node_coordinator',
        node=cic_node,
        is_active=True
    ).first()

    cnic_coord = UserRole.objects.filter(
        role='node_coordinator',
        node=cnic_node,
        is_active=True
    ).first()

    if not cic_coord or not cnic_coord:
        print("ERROR: No node coordinators found!")
        return

    print(f"Creating applications for:")
    print(f"  - {cic_node.code}: {cic_equipment.name} (coordinator: {cic_coord.user.email})")
    print(f"  - {cnic_node.code}: {cnic_equipment.name} (coordinator: {cnic_coord.user.email})")
    print()

    # Create applications
    apps_created = 0

    # App 1: CIC node
    app1_code = f'TEST-FEAS-CIC-{timezone.now().strftime("%m%d")}'
    app1, created = Application.objects.get_or_create(
        code=app1_code,
        defaults={
            'call': call,
            'applicant': applicants[0],
            'status': 'under_feasibility_review',
            'brief_description': f'Test feasibility review for {cic_node.code}',
            'applicant_name': applicants[0].get_full_name(),
            'applicant_entity': applicants[0].organization.name if applicants[0].organization else 'Test Org',
            'applicant_email': applicants[0].email,
            'applicant_phone': '+34 900 111 222',
            'project_title': f'Preclinical Imaging Study for {cic_node.name}',
            'project_code': 'PRJ-2026-FEAS-01',
            'funding_agency': 'Test Funding Agency',
            'project_type': 'national',
            'has_competitive_funding': False,
            'subject_area': 'bme',
            'service_modality': 'full_assistance',
            'specialization_area': 'preclinical',
            'scientific_relevance': 'Testing feasibility review workflow for CIC node.',
            'methodology_description': 'Standard preclinical imaging protocols.',
            'expected_contributions': 'Test data for development.',
            'impact_strengths': 'Testing purposes.',
            'socioeconomic_significance': 'Development testing.',
            'opportunity_criteria': 'Workflow validation.',
            'technical_feasibility_confirmed': True,
            'data_consent': True,
            'submitted_at': timezone.now(),
        }
    )

    if created:
        # Add equipment request
        RequestedAccess.objects.create(
            application=app1,
            equipment=cic_equipment,
            hours_requested=24
        )

        # Create pending feasibility review
        FeasibilityReview.objects.create(
            application=app1,
            node=cic_node,
            reviewer=cic_coord.user,
            is_feasible=None,
            comments='',
            reviewed_at=None
        )

        print(f"✓ Created {app1_code} for {cic_node.code}")
        apps_created += 1
    else:
        print(f"  Application {app1_code} already exists")

    # App 2: CNIC node
    app2_code = f'TEST-FEAS-CNIC-{timezone.now().strftime("%m%d")}'
    app2, created = Application.objects.get_or_create(
        code=app2_code,
        defaults={
            'call': call,
            'applicant': applicants[1 % len(applicants)],
            'status': 'under_feasibility_review',
            'brief_description': f'Test feasibility review for {cnic_node.code}',
            'applicant_name': applicants[1 % len(applicants)].get_full_name(),
            'applicant_entity': applicants[1 % len(applicants)].organization.name if applicants[1 % len(applicants)].organization else 'Test Org',
            'applicant_email': applicants[1 % len(applicants)].email,
            'applicant_phone': '+34 900 333 444',
            'project_title': f'Clinical Cardiovascular Study for {cnic_node.name}',
            'project_code': 'PRJ-2026-FEAS-02',
            'funding_agency': 'Test Funding Agency',
            'project_type': 'european',
            'has_competitive_funding': True,
            'subject_area': 'bme',
            'service_modality': 'presential',
            'specialization_area': 'clinical',
            'scientific_relevance': 'Testing feasibility review workflow for CNIC node.',
            'methodology_description': 'Clinical cardiovascular imaging protocols.',
            'expected_contributions': 'Test data for development.',
            'impact_strengths': 'Testing purposes.',
            'socioeconomic_significance': 'Development testing.',
            'opportunity_criteria': 'Workflow validation.',
            'technical_feasibility_confirmed': True,
            'data_consent': True,
            'submitted_at': timezone.now(),
        }
    )

    if created:
        # Add equipment request
        RequestedAccess.objects.create(
            application=app2,
            equipment=cnic_equipment,
            hours_requested=32
        )

        # Create pending feasibility review
        FeasibilityReview.objects.create(
            application=app2,
            node=cnic_node,
            reviewer=cnic_coord.user,
            is_feasible=None,
            comments='',
            reviewed_at=None
        )

        print(f"✓ Created {app2_code} for {cnic_node.code}")
        apps_created += 1
    else:
        print(f"  Application {app2_code} already exists")

    print()
    print(f"Summary: Created {apps_created} application(s)")
    print()
    print("You can now test feasibility review by logging in as:")
    print(f"  - {cic_coord.user.email} (for {cic_node.code})")
    print(f"  - {cnic_coord.user.email} (for {cnic_node.code})")
    print()

if __name__ == '__main__':
    create_feasibility_test_apps()
