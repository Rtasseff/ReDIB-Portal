"""
Forms for the calls app.
"""
from django import forms
from django.forms import inlineformset_factory
from django.utils import timezone
from datetime import time
from .models import Call, CallEquipmentAllocation
from core.models import Equipment


class CallForm(forms.ModelForm):
    """Form for creating and editing calls."""

    class Meta:
        model = Call
        fields = [
            'code', 'title', 'status', 'description', 'guidelines',
            'submission_start', 'submission_end', 'evaluation_deadline',
            'execution_start', 'execution_end'
        ]
        widgets = {
            'submission_start': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'submission_end': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'evaluation_deadline': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'execution_start': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'execution_end': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'description': forms.Textarea(attrs={
                'rows': 4,
                'class': 'form-control'
            }),
            'guidelines': forms.Textarea(attrs={
                'rows': 6,
                'class': 'form-control'
            }),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean(self):
        """Validate call dates and set time to 23:59 for all date fields."""
        cleaned_data = super().clean()

        # Set time to 23:59:59 for all date fields
        date_fields = ['submission_start', 'submission_end', 'evaluation_deadline',
                       'execution_start', 'execution_end']

        for field_name in date_fields:
            field_value = cleaned_data.get(field_name)
            if field_value:
                # If it's already a datetime, keep the date but set time to 23:59:59
                # If it's a date object, convert to datetime with time 23:59:59
                if hasattr(field_value, 'date'):
                    # It's a datetime
                    date_only = field_value.date()
                else:
                    # It's a date
                    date_only = field_value

                # Create datetime with time set to 23:59:59
                from datetime import datetime
                dt = datetime.combine(date_only, time(23, 59, 59))

                # Make it timezone-aware
                if timezone.is_naive(dt):
                    dt = timezone.make_aware(dt)

                cleaned_data[field_name] = dt

        submission_start = cleaned_data.get('submission_start')
        submission_end = cleaned_data.get('submission_end')
        evaluation_deadline = cleaned_data.get('evaluation_deadline')
        execution_start = cleaned_data.get('execution_start')
        execution_end = cleaned_data.get('execution_end')

        # Submission dates validation
        if submission_start and submission_end:
            if submission_end.date() < submission_start.date():
                raise forms.ValidationError("Submission end date must be on or after submission start date.")

        # Evaluation deadline validation
        if submission_end and evaluation_deadline:
            if evaluation_deadline.date() <= submission_end.date():
                raise forms.ValidationError("Evaluation deadline must be after submission end date.")

        # Execution dates validation
        if execution_start and execution_end:
            if execution_end.date() < execution_start.date():
                raise forms.ValidationError("Execution end date must be on or after execution start date.")

        return cleaned_data


class CallEquipmentAllocationForm(forms.ModelForm):
    """Form for allocating equipment to a call."""

    class Meta:
        model = CallEquipmentAllocation
        fields = ['equipment']
        widgets = {
            'equipment': forms.Select(attrs={'class': 'form-select'}),
        }


# Formset for managing equipment allocations inline (base factory)
# Note: extra parameter is set dynamically in views for create vs edit
CallEquipmentFormSet = inlineformset_factory(
    Call,
    CallEquipmentAllocation,
    form=CallEquipmentAllocationForm,
    extra=0,  # Default for edit view
    can_delete=True,
    min_num=0,
    validate_min=False
)


def get_equipment_formset_for_create(active_equipment_count):
    """
    Returns a formset factory configured for call creation.
    Sets 'extra' to match the number of active equipment items.
    """
    return inlineformset_factory(
        Call,
        CallEquipmentAllocation,
        form=CallEquipmentAllocationForm,
        extra=active_equipment_count,  # One form per equipment item
        can_delete=True,
        min_num=0,
        validate_min=False
    )
