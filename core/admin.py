"""
Django admin configuration for core models.
"""

from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from simple_history.admin import SimpleHistoryAdmin
from .models import Organization, Node, Equipment, User, UserRole


# Choices for the multi-select widget on UserRole.areas in admin
EVALUATOR_AREA_CHOICES = [
    ('clinical', 'Clinical'),
    ('preclinical', 'Preclinical'),
    ('radiochemistry', 'Radiochemistry'),
]


class UserRoleAdminForm(forms.ModelForm):
    """ModelForm for UserRole admin that exposes `areas` as a checkbox multi-select."""

    areas = forms.MultipleChoiceField(
        choices=EVALUATOR_AREA_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        help_text='Select all specialization areas this user can evaluate (only meaningful for evaluators).',
    )

    class Meta:
        model = UserRole
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pre-populate from the existing comma-separated string
        if self.instance and self.instance.pk and self.instance.areas:
            self.initial['areas'] = self.instance.area_list

    def clean_areas(self):
        # MultipleChoiceField returns a list; serialize back to a comma-separated string
        return ','.join(self.cleaned_data.get('areas', []))


@admin.register(Organization)
class OrganizationAdmin(SimpleHistoryAdmin):
    list_display = ['name', 'organization_type', 'country', 'created_at']
    list_filter = ['organization_type', 'country']
    search_fields = ['name', 'address']
    ordering = ['name']


@admin.register(Node)
class NodeAdmin(SimpleHistoryAdmin):
    list_display = ['code', 'name', 'director', 'location', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'code', 'location']
    ordering = ['code']
    autocomplete_fields = ['director']


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
        ('Preferences', {'fields': ('receive_call_notifications', 'auto_data_consent')}),
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
    form = UserRoleAdminForm
    list_display = ['user', 'role', 'node', 'areas', 'is_active', 'assigned_at']
    list_filter = ['role', 'node', 'is_active']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    ordering = ['-assigned_at']
