"""
Forms for the applications app - 5-step application wizard.
"""
from django import forms
from django.forms import inlineformset_factory
from .models import Application, RequestedAccess, FeasibilityReview
from core.models import Equipment


class ApplicationStep1Form(forms.ModelForm):
    """Step 1: Applicant Information & Brief Description"""

    class Meta:
        model = Application
        fields = [
            'applicant_name',
            'applicant_orcid',
            'applicant_entity',
            'applicant_email',
            'applicant_phone',
            'brief_description'
        ]
        widgets = {
            'applicant_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Full name'
            }),
            'applicant_orcid': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ORCID identifier (optional)'
            }),
            'applicant_entity': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Institution or organization'
            }),
            'applicant_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Contact email'
            }),
            'applicant_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Contact phone number'
            }),
            'brief_description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'One-line summary of your project (max 100 characters)',
                'maxlength': '100'
            }),
        }
        labels = {
            'applicant_name': 'Name and Surname',
            'applicant_orcid': 'ORCID',
            'applicant_entity': 'Entity',
            'applicant_email': 'Email',
            'applicant_phone': 'Phone',
            'brief_description': 'Brief Description'
        }
        help_texts = {
            'applicant_name': 'Your full name',
            'applicant_orcid': 'Optional ORCID identifier',
            'applicant_entity': 'Your institution or organization',
            'applicant_email': 'Contact email address',
            'applicant_phone': 'Contact phone number',
            'brief_description': 'Provide a concise summary of your research project'
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Auto-populate applicant fields from user profile if creating new application
        if user and not self.instance.pk:
            self.initial['applicant_name'] = user.get_full_name() or f"{user.first_name} {user.last_name}".strip()
            self.initial['applicant_email'] = user.email
            if hasattr(user, 'organization') and user.organization:
                self.initial['applicant_entity'] = user.organization
            if hasattr(user, 'phone') and user.phone:
                self.initial['applicant_phone'] = user.phone

        # Make all fields required except ORCID
        self.fields['applicant_name'].required = True
        self.fields['applicant_orcid'].required = False
        self.fields['applicant_entity'].required = True
        self.fields['applicant_email'].required = True
        self.fields['applicant_phone'].required = True


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
        help_texts = {
            'service_modality': (
                '<strong>Full assistance:</strong> The requested experiments are carried out by ReDIB technical staff, '
                'following the user\'s requirements, but without the user\'s physical presence at the centre. '
                '<strong>In-person:</strong> The user can participate and assist ReDIB technical staff during the development '
                'of the experiments. '
                '<strong>Self-service:</strong> The user, after ad hoc training by ReDIB, directly uses the infrastructure '
                'to which he or she has been granted access, always under the supervision of ICTS technical staff. '
                '<em>Not all service modalities are available for all installations. In case of doubt, please contact ReDIB technical staff.</em>'
            ),
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
        help_texts = {
            'hours_requested': (
                'Requested access time: cannot exceed the maximum offered in the AAC call for the indicated installation. '
                'If you are unable to estimate the access time required to undertake the experimentation associated with the '
                'Proposal, consult with the ReDIB node involved.'
            ),
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
                'placeholder': 'Justify your expectations for future scientific-technical contributions and express your commitment to publish and disseminate the ICTS access you are now requesting...'
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
        help_texts = {
            'expected_contributions': 'Justify your expectations for future scientific-technical contributions and express your commitment to publish and disseminate the ICTS access you are now requesting...',
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
            'data_consent': 'Having been informed of the processing to which my personal data will be subject, I freely give my consent to such processing',
        }
        help_texts = {
            'technical_feasibility_confirmed': (
                'In order for an COA Proposal to be approved and prioritized, it is necessary to ensure that ReDIB, '
                'at any of its nodes, can technically undertake the requested service or experimentation. Therefore, '
                'it is recommended that AAC applicants consult in advance about the TECHNICAL FEASIBILITY of their Proposal, '
                'contacting the ReDIB node most directly involved in it, and, in any case, provide in this form all the '
                'details of the experimentation that the Proposal contemplates to be carried out at ReDIB facilities.'
            ),
            'data_consent': (
                'The personal data collected in this document will be incorporated and processed in the file "ICTS ReDIB USERS", '
                'the purpose of which is to receive and evaluate requests for use of the ReDIB facilities. The user may exercise '
                'their rights of access, rectification, deletion and portability of their data before the nodes that make up ReDIB, '
                'as entities jointly responsible for the "ICTS ReDIB USERS" file, through the procedure for exercising personal data '
                'rights available on the ReDIB website: www.redib.net. All of which is reported in compliance with article 6 of '
                'Organic Law 3/2018, of December 5, on the Protection of Personal Data and guarantee of digital rights.'
            ),
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

    # Override is_feasible to use radio buttons instead of checkbox
    is_feasible = forms.TypedChoiceField(
        choices=[
            (True, 'Approve - Technically feasible'),
            (False, 'Reject - Not feasible'),
        ],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        coerce=lambda x: x == 'True',  # Convert string to boolean
        label='Feasibility Decision',
        required=True,
        empty_value=None
    )

    class Meta:
        model = FeasibilityReview
        fields = ['is_feasible', 'comments']
        widgets = {
            'comments': forms.Textarea(attrs={
                'rows': 5,
                'class': 'form-control',
                'placeholder': 'Provide comments on technical feasibility, resource availability, or any concerns...'
            }),
        }
        labels = {
            'comments': 'Review Comments',
        }

    def clean(self):
        """Validate that comments are provided if rejected"""
        cleaned_data = super().clean()
        is_feasible = cleaned_data.get('is_feasible')
        comments = cleaned_data.get('comments')

        # Require comments if rejecting (is_feasible == False)
        if is_feasible is False and not comments:
            raise forms.ValidationError(
                "Please provide comments explaining why the application is not feasible."
            )

        return cleaned_data


# =============================================================================
# Phase 6: Resolution Forms
# =============================================================================

class ApplicationResolutionForm(forms.ModelForm):
    """
    Form for coordinators to apply resolution to individual applications.

    Business Rules (Critical):
    - Competitive funding apps CANNOT be rejected (choice removed dynamically)
    - Resolution comments are recommended but not required
    """

    class Meta:
        model = Application
        fields = ['resolution', 'resolution_comments']
        widgets = {
            'resolution': forms.RadioSelect(attrs={'class': 'form-check-input'}),
            'resolution_comments': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Optional: Add comments about this resolution decision...'
            })
        }

    def __init__(self, *args, **kwargs):
        """
        Customize form based on application properties.

        If application has competitive funding, remove 'rejected' option.
        """
        # Extract application instance from kwargs
        self.application = kwargs.pop('application', None)
        super().__init__(*args, **kwargs)

        # Remove 'rejected' choice if has_competitive_funding
        if self.application and self.application.has_competitive_funding:
            # Filter out rejected option
            original_choices = self.fields['resolution'].choices
            filtered_choices = [
                choice for choice in original_choices
                if choice[0] in ['accepted', 'pending']
            ]
            self.fields['resolution'].choices = filtered_choices

            # Add help text
            self.fields['resolution'].help_text = (
                "This application has competitive funding and cannot be rejected. "
                "It must be either accepted or marked as pending."
            )

    def clean(self):
        """
        Validate resolution business rules.
        """
        cleaned_data = super().clean()
        resolution = cleaned_data.get('resolution')

        # Validate: competitive funding cannot be rejected
        if self.application and self.application.has_competitive_funding:
            if resolution == 'rejected':
                raise forms.ValidationError(
                    "Applications with competitive funding cannot be rejected. "
                    "They must be either accepted or marked as pending."
                )

        return cleaned_data


class BulkResolutionForm(forms.Form):
    """
    Form for bulk auto-allocation of resolutions by priority.

    Allows coordinator to set threshold score and auto-pending behavior.
    """

    threshold_score = forms.DecimalField(
        min_value=1.0,
        max_value=5.0,
        initial=3.0,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.1',
            'placeholder': '3.0'
        }),
        help_text="Minimum score for acceptance (1.0-5.0). Applications below this threshold will be rejected."
    )

    auto_pending = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Automatically mark applications as 'pending' when hours are exhausted (instead of rejected)"
    )

    def clean_threshold_score(self):
        """Validate threshold score is within valid range."""
        threshold = self.cleaned_data.get('threshold_score')
        if threshold < 1.0 or threshold > 5.0:
            raise forms.ValidationError("Threshold score must be between 1.0 and 5.0")
        return threshold
