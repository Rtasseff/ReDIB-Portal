"""
URL configuration for the calls app.
"""
from django.urls import path
from . import views

app_name = 'calls'

urlpatterns = [
    # Public views
    path('', views.public_call_list, name='public_list'),
    path('<int:pk>/', views.public_call_detail, name='public_detail'),
    path('<int:pk>/consult/', views.public_consult_request, name='public_consult'),
    path('<int:pk>/consult/thanks/', views.public_consult_thanks, name='public_consult_thanks'),

    # Coordinator views
    path('manage/', views.coordinator_dashboard, name='coordinator_dashboard'),
    path('create/', views.call_create, name='create'),
    path('<int:pk>/edit/', views.call_edit, name='call_edit'),
    path('<int:pk>/detail/', views.call_detail, name='detail'),
    path('<int:pk>/consult-requests/', views.consult_requests, name='consult_requests'),
    path('<int:pk>/announce/', views.call_announce, name='announce'),
    path('<int:pk>/publish/', views.call_publish, name='publish'),
    path('<int:pk>/close/', views.call_close, name='close'),
    path('<int:pk>/resolve/', views.call_resolve, name='resolve'),
    path('<int:pk>/release-resolutions/', views.call_release_resolutions, name='release_resolutions'),
    path('<int:pk>/remind/evaluators/', views.remind_evaluators, name='remind_evaluators'),
    path('<int:pk>/remind/feasibility/', views.remind_feasibility, name='remind_feasibility'),
    path('<int:pk>/delete/', views.call_delete, name='delete'),
]
