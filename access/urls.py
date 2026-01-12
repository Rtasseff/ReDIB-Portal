"""
URL configuration for access app - Phase 8 & 9: Scheduling, Tracking, Publications.
"""
from django.urls import path
from . import views

app_name = 'access'

urlpatterns = [
    # Phase 7/8: Access handoff and scheduling
    path('scheduling/', views.node_scheduling, name='node_scheduling'),
    path('tracking/', views.access_tracking, name='access_tracking'),
    path('handoff/', views.applicant_handoff_dashboard, name='applicant_handoff'),
    path('complete/<int:application_id>/', views.mark_application_complete, name='mark_complete'),

    # Phase 9: Publication tracking
    path('publications/', views.publication_list, name='publication_list'),
    path('publications/submit/', views.publication_submit, name='publication_submit'),
]
