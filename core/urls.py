"""
URL configuration for the core app.
"""
from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile, name='profile'),
    path('help/user-guide/', views.user_guide, name='user_guide'),
    path('', views.dashboard, name='home'),  # Redirect root to dashboard
]
