"""
Django admin configuration for core models.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from simple_history.admin import SimpleHistoryAdmin
from .models import Organization, Node, Equipment, User, UserRole


@admin.register(Organization)
class OrganizationAdmin(SimpleHistoryAdmin):
    list_display = ['name', 'organization_type', 'country', 'created_at']
    list_filter = ['organization_type', 'country']
    search_fields = ['name', 'address']
    ordering = ['name']


@admin.register(Node)
class NodeAdmin(SimpleHistoryAdmin):
    list_display = ['code', 'name', 'location', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'code', 'location']
    ordering = ['code']


@admin.register(Equipment)
class EquipmentAdmin(SimpleHistoryAdmin):
    list_display = ['name', 'node', 'category', 'is_essential', 'is_active']
    list_filter = ['node', 'category', 'is_essential', 'is_active']
    search_fields = ['name', 'description']
    ordering = ['node', 'name']


@admin.register(User)
class UserAdmin(BaseUserAdmin, SimpleHistoryAdmin):
    list_display = ['email', 'first_name', 'last_name', 'organization', 'is_staff', 'date_joined']
    list_filter = ['is_staff', 'is_superuser', 'is_active', 'organization']
    search_fields = ['email', 'first_name', 'last_name', 'orcid']
    ordering = ['email']

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'organization', 'orcid', 'phone', 'position')}),
        ('Preferences', {'fields': ('receive_call_notifications',)}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'password1', 'password2'),
        }),
    )


@admin.register(UserRole)
class UserRoleAdmin(SimpleHistoryAdmin):
    list_display = ['user', 'role', 'node', 'area', 'is_active', 'assigned_at']
    list_filter = ['role', 'node', 'area', 'is_active']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    ordering = ['-assigned_at']
