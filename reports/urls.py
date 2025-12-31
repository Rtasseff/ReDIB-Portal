"""
URL configuration for reports app - Phase 10: Reporting & Statistics.
"""
from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.statistics_dashboard, name='statistics'),
    path('call/<int:call_id>/export/', views.export_call_report, name='export_call_report'),
    path('history/', views.report_history, name='history'),
]
