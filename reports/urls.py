"""
URL configuration for reports app - Phase 10: Reporting & Statistics.
"""
from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.statistics_dashboard, name='statistics'),
    path('call/<int:call_id>/export/', views.export_call_report, name='export_call_report'),
    path('call/<int:call_id>/resolution/', views.resolution_report, name='resolution_report'),
    path('call/<int:call_id>/resolution/csv/<str:lang>/', views.resolution_report_csv, name='resolution_report_csv'),
    path('history/', views.report_history, name='history'),
]
