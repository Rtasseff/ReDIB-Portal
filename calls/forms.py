"""
Forms for the calls app.
"""
from django import forms
from django.forms import inlineformset_factory
from django.utils import timezone
from datetime import time
from .models import Call, CallEquipmentAllocation, ConsultRequest
from core.models import Equipment


class CallForm(forms.ModelForm):
    """Form for creating and editing calls."""

    class Meta:
        model = Call
        fields = [
            'code', 'title', 'description', 'guidelines',
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
        }

    def clean(self):
        """Validate call dates and normalize times.

        Start fields open at 00:00:00 of the chosen day; end/deadline fields
        close at 23:59:59 of the chosen day. This matches how users think
        about "opens on X, closes on Y".
        """
        cleaned_data = super().clean()

        start_of_day_fields = ['submission_start', 'execution_start']
        end_of_day_fields = ['submission_end', 'evaluation_deadline', 'execution_end']

        from datetime import datetime

        for field_name in start_of_day_fields + end_of_day_fields:
            field_value = cleaned_data.get(field_name)
            if not field_value:
                continue

            date_only = field_value.date() if hasattr(field_value, 'date') else field_value
            target_time = time(0, 0, 0) if field_name in start_of_day_fields else time(23, 59, 59)
            dt = datetime.combine(date_only, target_time)

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


class ConsultRequestForm(forms.ModelForm):
    """Public "request a consult" form on a call page.

    Anonymous submissions are allowed, so the form carries a honeypot field
    (`website`) that real users never see and never fill in.
    """

    equipment = forms.ModelMultipleChoiceField(
        queryset=Equipment.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        error_messages={
            'required': 'Select at least one instrument you would like to discuss.',
            'invalid_choice': 'That equipment is not available on this call.',
            'invalid_pk_value': 'That equipment is not available on this call.',
        },
    )

    # Honeypot: hidden from humans via CSS, bots fill it in.
    website = forms.CharField(
        required=False,
        label='Website',
        widget=forms.TextInput(attrs={
            'autocomplete': 'off',
            'tabindex': '-1',
            'class': 'consult-hp',
        }),
    )

    class Meta:
        model = ConsultRequest
        fields = ['name', 'email', 'phone', 'organization', 'message']
        labels = {
            'name': 'Your name',
            'email': 'Email',
            'phone': 'Phone (optional)',
            'organization': 'Institution / company (optional)',
            'message': 'What would you like to discuss? (optional)',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'organization': forms.TextInput(attrs={'class': 'form-control'}),
            'message': forms.Textarea(attrs={
                'rows': 5,
                'class': 'form-control',
                'placeholder': 'Briefly describe your study, the imaging you have '
                               'in mind, or the questions you have for the node.',
            }),
        }

    def __init__(self, *args, call=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.call = call
        self.fields['equipment'].queryset = Equipment.objects.filter(
            call_allocations__call=call
        ).select_related('node__organization').order_by('node__code', 'name')

    def clean_website(self):
        """Honeypot — any value at all means this was not a human."""
        if self.cleaned_data.get('website'):
            raise forms.ValidationError('Your submission could not be processed.')
        return ''

    def grouped_equipment(self):
        """Equipment choices grouped by node, for checkbox rendering.

        Returns [{'node': node, 'items': [{'equipment': eq, 'checked': bool}]}]
        preserving whatever the user had ticked on a redisplayed form.
        """
        raw_selection = self['equipment'].value() or []
        selected = {str(value) for value in raw_selection}

        groups = []
        for equipment in self.fields['equipment'].queryset:
            if not groups or groups[-1]['node'] != equipment.node:
                groups.append({'node': equipment.node, 'items': []})
            groups[-1]['items'].append({
                'equipment': equipment,
                'checked': str(equipment.pk) in selected,
            })
        return groups


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
