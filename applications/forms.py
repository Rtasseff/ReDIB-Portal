"""
Forms for the applications app - 5-step application wizard.
"""
from django import forms
from django.forms import inlineformset_factory
from .models import Application, RequestedAccess, FeasibilityReview
from core.models import Equipment


class ApplicationStep1Form(forms.ModelForm):
    """Step 1: Basic Info & Brief Description"""

    class Meta:
        model = Application
        fields = ['brief_description']
        widgets = {
            'brief_description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'One-line summary of your project (max 100 characters)',
                'maxlength': '100'
            }),
        }
        labels = {
            'brief_description': 'Brief Description'
        }
        help_texts = {
            'brief_description': 'Provide a concise summary of your research project'
        }


class ApplicationStep2Form(forms.ModelForm):
    """Step 2: Funding & Project Information"""

    class Meta:
        model = Application
        fields = [
            'project_title', 'project_code', 'funding_agency',
            'project_type', 'has_competitive_funding', 'subject_area'
        ]
        widgets = {
            'project_title': forms.TextInput(attrs={'class': 'form-control'}),
            'project_code': forms.TextInput(attrs={'class': 'form-control'}),
            'funding_agency': forms.TextInput(attrs={'class': 'form-control'}),
            'project_type': forms.Select(attrs={'class': 'form-select'}),
            'has_competitive_funding': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'subject_area': forms.Select(attrs={'class': 'form-select'}),
        }


class ApplicationStep3Form(forms.ModelForm):
    """Step 3: Service Modality & Specialization"""

    class Meta:
        model = Application
        fields = ['service_modality', 'specialization_area']
        widgets = {
            'service_modality': forms.RadioSelect(attrs={'class': 'form-check-input'}),
            'specialization_area': forms.RadioSelect(attrs={'class': 'form-check-input'}),
        }


class RequestedAccessForm(forms.ModelForm):
    """Equipment access request (used in formset)"""

    class Meta:
        model = RequestedAccess
        fields = ['equipment', 'hours_requested']
        widgets = {
            'equipment': forms.Select(attrs={'class': 'form-select'}),
            'hours_requested': forms.NumberInput(attrs={
                'step': '0.5',
                'min': '0.5',
                'class': 'form-control'
            }),
        }

    def __init__(self, *args, **kwargs):
        call = kwargs.pop('call', None)
        super().__init__(*args, **kwargs)

        if call:
            # Only show equipment with allocations in this call
            available_equipment = Equipment.objects.filter(
                call_allocations__call=call,
                is_active=True
            ).select_related('node').order_by('node__code', 'name')
            self.fields['equipment'].queryset = available_equipment


# Formset for equipment requests
RequestedAccessFormSet = inlineformset_factory(
    Application,
    RequestedAccess,
    form=RequestedAccessForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True
)


class ApplicationStep4Form(forms.ModelForm):
    """Step 4: Scientific Content (6 evaluation criteria)"""

    class Meta:
        model = Application
        fields = [
            'scientific_relevance',
            'methodology_description',
            'expected_contributions',
            'impact_strengths',
            'socioeconomic_significance',
            'opportunity_criteria'
        ]
        widgets = {
            'scientific_relevance': forms.Textarea(attrs={
                'rows': 5,
                'class': 'form-control',
                'placeholder': 'Describe the scientific and technical relevance, quality, and originality of your project...'
            }),
            'methodology_description': forms.Textarea(attrs={
                'rows': 5,
                'class': 'form-control',
                'placeholder': 'Describe your experimental and methodological design...'
            }),
            'expected_contributions': forms.Textarea(attrs={
                'rows': 5,
                'class': 'form-control',
                'placeholder': 'Describe expected future contributions and dissemination plans...'
            }),
            'impact_strengths': forms.Textarea(attrs={
                'rows': 5,
                'class': 'form-control',
                'placeholder': 'Describe the strengths and potential for advancement of knowledge...'
            }),
            'socioeconomic_significance': forms.Textarea(attrs={
                'rows': 5,
                'class': 'form-control',
                'placeholder': 'Describe the social, economic, and industrial significance...'
            }),
            'opportunity_criteria': forms.Textarea(attrs={
                'rows': 5,
                'class': 'form-control',
                'placeholder': 'Describe opportunity criteria and translational impact...'
            }),
        }
        labels = {
            'scientific_relevance': '1. Scientific and Technical Relevance',
            'methodology_description': '2. Methodology and Experimental Design',
            'expected_contributions': '3. Expected Contributions',
            'impact_strengths': '4. Impact and Advancement of Knowledge',
            'socioeconomic_significance': '5. Socioeconomic Significance',
            'opportunity_criteria': '6. Opportunity and Translational Impact',
        }


class ApplicationStep5Form(forms.ModelForm):
    """Step 5: Declarations & Consent"""

    class Meta:
        model = Application
        fields = [
            'technical_feasibility_confirmed',
            'uses_animals',
            'has_animal_ethics',
            'uses_humans',
            'has_human_ethics',
            'data_consent'
        ]
        widgets = {
            'technical_feasibility_confirmed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'uses_animals': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_animal_ethics': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'uses_humans': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_human_ethics': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'data_consent': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'technical_feasibility_confirmed': 'I have confirmed technical feasibility with the ReDIB node',
            'uses_animals': 'This proposal involves experimental animals',
            'has_animal_ethics': 'I have ethics committee approval for animal use',
            'uses_humans': 'This proposal involves human subjects',
            'has_human_ethics': 'I have ethics committee approval for human subjects',
            'data_consent': 'I consent to data processing as described in the privacy policy (Required)',
        }

    def clean(self):
        """Validate declarations"""
        cleaned_data = super().clean()

        # Validate animal ethics if uses animals
        if cleaned_data.get('uses_animals') and not cleaned_data.get('has_animal_ethics'):
            raise forms.ValidationError(
                "If using animals, you must have ethics committee approval."
            )

        # Validate human ethics if uses humans
        if cleaned_data.get('uses_humans') and not cleaned_data.get('has_human_ethics'):
            raise forms.ValidationError(
                "If using human subjects, you must have ethics committee approval."
            )

        # Data consent is required
        if not cleaned_data.get('data_consent'):
            raise forms.ValidationError(
                "You must consent to data processing to submit your application."
            )

        return cleaned_data


class FeasibilityReviewForm(forms.ModelForm):
    """Feasibility review by node coordinator"""

    class Meta:
        model = FeasibilityReview
        fields = ['decision', 'comments']
        widgets = {
            'decision': forms.RadioSelect(attrs={'class': 'form-check-input'}),
            'comments': forms.Textarea(attrs={
                'rows': 5,
                'class': 'form-control',
                'placeholder': 'Provide comments on technical feasibility, resource availability, or any concerns...'
            }),
        }
        labels = {
            'decision': 'Feasibility Decision',
            'comments': 'Review Comments',
        }

    def clean(self):
        """Validate that comments are provided if rejected"""
        cleaned_data = super().clean()
        decision = cleaned_data.get('decision')
        comments = cleaned_data.get('comments')

        if decision == 'rejected' and not comments:
            raise forms.ValidationError(
                "Please provide comments explaining why the application is not feasible."
            )

        return cleaned_data
