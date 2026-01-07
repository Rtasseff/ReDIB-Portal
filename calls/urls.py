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

    # Coordinator views
    path('manage/', views.coordinator_dashboard, name='coordinator_dashboard'),
    path('create/', views.call_create, name='create'),
    path('<int:pk>/edit/', views.call_edit, name='call_edit'),
    path('<int:pk>/detail/', views.call_detail, name='detail'),
    path('<int:pk>/publish/', views.call_publish, name='publish'),
    path('<int:pk>/close/', views.call_close, name='close'),
    path('<int:pk>/delete/', views.call_delete, name='delete'),
]
