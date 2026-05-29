"""
URL configuration for the newsletters app.
"""
from django.urls import path

from . import views

app_name = 'newsletters'

urlpatterns = [
    path('', views.newsletter_list, name='list'),
    path('<slug:slug>/', views.newsletter_detail, name='detail'),
    path('<slug:slug>/raw/', views.newsletter_raw, name='raw'),
]
