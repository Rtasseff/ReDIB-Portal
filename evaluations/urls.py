"""
URL configuration for evaluations app - Phase 4 implementation.
"""
from django.urls import path
from . import views

app_name = 'evaluations'

urlpatterns = [
    # Evaluator views
    path('', views.evaluator_dashboard, name='my_evaluations'),
    path('<int:pk>/', views.evaluation_detail, name='evaluation_detail'),

    # Coordinator assignment views
    path('assign/', views.assignment_dashboard, name='assignment_dashboard'),
    path('assign/call/<int:call_id>/', views.call_assignment_detail, name='call_assignment_detail'),
    path('assign/call/<int:call_id>/auto/', views.auto_assign_call, name='auto_assign_call'),
    path('assign/application/<int:application_id>/manual/', views.manual_assign_evaluator, name='manual_assign_evaluator'),
    path('assign/evaluation/<int:evaluation_id>/remove/', views.remove_evaluator_assignment, name='remove_evaluator_assignment'),
]
