"""
Forms for the calls app.
"""
from django import forms
from django.forms import inlineformset_factory
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
            'submission_start': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
            'submission_end': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
            'evaluation_deadline': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
            'execution_start': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
            'execution_end': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
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
        """Validate call dates."""
        cleaned_data = super().clean()
        submission_start = cleaned_data.get('submission_start')
        submission_end = cleaned_data.get('submission_end')
        evaluation_deadline = cleaned_data.get('evaluation_deadline')
        execution_start = cleaned_data.get('execution_start')
        execution_end = cleaned_data.get('execution_end')

        # Submission dates validation
        if submission_start and submission_end:
            if submission_end <= submission_start:
                raise forms.ValidationError("Submission end date must be after submission start date.")

        # Evaluation deadline validation
        if submission_end and evaluation_deadline:
            if evaluation_deadline <= submission_end:
                raise forms.ValidationError("Evaluation deadline must be after submission end date.")

        # Execution dates validation
        if execution_start and execution_end:
            if execution_end <= execution_start:
                raise forms.ValidationError("Execution end date must be after execution start date.")

        return cleaned_data


class CallEquipmentAllocationForm(forms.ModelForm):
    """Form for allocating equipment hours to a call."""

    class Meta:
        model = CallEquipmentAllocation
        fields = ['equipment', 'hours_offered']
        widgets = {
            'equipment': forms.Select(attrs={'class': 'form-select'}),
            'hours_offered': forms.NumberInput(attrs={
                'step': '0.5',
                'min': '0',
                'class': 'form-control'
            }),
        }


# Formset for managing equipment allocations inline
CallEquipmentFormSet = inlineformset_factory(
    Call,
    CallEquipmentAllocation,
    form=CallEquipmentAllocationForm,
    extra=3,  # Show 3 empty forms by default
    can_delete=True,
    min_num=0,
    validate_min=False
)
