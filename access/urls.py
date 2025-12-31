"""
URL configuration for access app - Phase 9: Publication Tracking.
"""
from django.urls import path
from . import views

app_name = 'access'

urlpatterns = [
    # Phase 9: Publication tracking
    path('publications/', views.publication_list, name='publication_list'),
    path('publications/submit/', views.publication_submit, name='publication_submit'),
]
