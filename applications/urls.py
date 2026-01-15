"""
URL configuration for the applications app.
"""
from django.urls import path
from . import views

app_name = 'applications'

urlpatterns = [
    # Applicant views
    path('my-applications/', views.my_applications, name='my_applications'),
    path('<int:pk>/', views.application_detail, name='detail'),
    path('create/<int:call_pk>/', views.application_create, name='create'),
    path('<int:pk>/step2/', views.application_edit_step2, name='edit_step2'),
    path('<int:pk>/step3/', views.application_edit_step3, name='edit_step3'),
    path('<int:pk>/step4/', views.application_edit_step4, name='edit_step4'),
    path('<int:pk>/step5/', views.application_edit_step5, name='edit_step5'),
    path('<int:pk>/preview/', views.application_preview, name='preview'),
    path('<int:pk>/submit/', views.application_submit, name='submit'),
    path('<int:pk>/download-pdf/', views.download_application_pdf, name='download_pdf'),
    path('<int:pk>/upload-signed/', views.upload_signed_pdf, name='upload_signed_pdf'),

    # Stub URL for edit_step1 (redirects to step2 since step1 is only for create)
    path('<int:pk>/step1/', views.application_edit_step2, name='edit_step1'),

    # Node coordinator views - Phase 3: Feasibility Review
    path('feasibility/', views.feasibility_queue, name='feasibility_queue'),
    path('feasibility/<int:pk>/review/', views.feasibility_review, name='feasibility_review'),

    # Coordinator views - Phase 6: Resolution
    path('resolution/', views.resolution_dashboard, name='resolution_dashboard'),
    path('resolution/call/<int:call_id>/', views.call_resolution_detail, name='call_resolution_detail'),
    path('resolution/application/<int:application_id>/', views.application_resolution, name='application_resolution'),
    path('resolution/call/<int:call_id>/bulk/', views.bulk_resolution, name='bulk_resolution'),
    path('resolution/call/<int:call_id>/finalize/', views.finalize_resolution, name='finalize_resolution'),

    # Node Coordinator views - Phase 6: Node Resolution
    path('node-resolution/', views.node_resolution_queue, name='node_resolution_queue'),
    path('node-resolution/<int:application_id>/node/<int:node_id>/', views.node_resolution_review, name='node_resolution_review'),

    # Equipment Completion Tracking
    path('<int:application_id>/equipment/<int:requested_access_id>/mark-done/', views.mark_equipment_done, name='mark_equipment_done'),
    path('<int:application_id>/equipment/<int:requested_access_id>/node-confirm-done/', views.node_confirm_equipment_done, name='node_confirm_equipment_done'),

    # Phase 7: Acceptance & Handoff
    path('<int:pk>/accept/', views.application_acceptance, name='application_acceptance'),
    path('handoff/', views.handoff_dashboard, name='handoff_dashboard'),
    path('<int:pk>/mark-completed/', views.mark_completed, name='mark_completed'),
]
