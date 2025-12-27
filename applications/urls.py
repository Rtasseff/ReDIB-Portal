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

    # Stub URL for edit_step1 (redirects to step2 since step1 is only for create)
    path('<int:pk>/step1/', views.application_edit_step2, name='edit_step1'),

    # Node coordinator views - stubs for Phase 3
    path('feasibility/', views.my_applications, name='feasibility_queue'),
    path('feasibility/<int:pk>/review/', views.my_applications, name='feasibility_review'),

    # Coordinator views - stubs for Phase 6
    path('resolution/', views.my_applications, name='resolution_dashboard'),
]
