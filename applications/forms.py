"""
Forms for the applications app - 5-step application wizard.
"""
from django import forms
from django.forms import inlineformset_factory
import json
from .models import Application, RequestedAccess, FeasibilityReview, FundingAgency, PROJECT_TYPES
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
            'project_name',
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
            'project_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Name of your research project'
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
            'project_name': 'Project Name',
            'brief_description': 'Project Summary'
        }
        help_texts = {
            'applicant_name': 'Your full name',
            'applicant_orcid': 'Optional ORCID identifier',
            'applicant_entity': 'Your institution or organization',
            'applicant_email': 'Contact email address',
            'applicant_phone': 'Contact phone number',
            'project_name': 'The name of your research project',
            'brief_description': 'Provide a concise summary of your research project'
        }

    def __init__(self, *args, **kwargs):
        self._user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Auto-populate from user profile (both new and existing applications)
        if self._user:
            self.initial['applicant_name'] = self._user.get_full_name() or f"{self._user.first_name} {self._user.last_name}".strip()
            self.initial['applicant_email'] = self._user.email
            if self._user.organization:
                self.initial['applicant_entity'] = str(self._user.organization)
            if self._user.phone:
                self.initial['applicant_phone'] = self._user.phone
            if self._user.orcid:
                self.initial['applicant_orcid'] = self._user.orcid

            # Make profile-derived fields read-only (disabled fields don't submit data)
            for field_name in ['applicant_name', 'applicant_email', 'applicant_entity', 'applicant_phone', 'applicant_orcid']:
                self.fields[field_name].disabled = True

        # Make all fields required except ORCID
        self.fields['applicant_name'].required = True
        self.fields['applicant_orcid'].required = False
        self.fields['applicant_entity'].required = True
        self.fields['applicant_email'].required = True
        self.fields['applicant_phone'].required = True
        self.fields['project_name'].required = True


class FundingAgencyWithOtherChoiceField(forms.ModelChoiceField):
    """
    A ModelChoiceField that accepts the '__other__' sentinel value as valid.
    The form's clean() method is responsible for converting '__other__' into a real
    FundingAgency instance based on the new_funding_agency_name field.
    """
    OTHER_SENTINEL = '__other__'

    def to_python(self, value):
        if value == self.OTHER_SENTINEL:
            return self.OTHER_SENTINEL
        return super().to_python(value)

    def validate(self, value):
        if value == self.OTHER_SENTINEL:
            return
        super().validate(value)


class ApplicationStep2Form(forms.ModelForm):
    """Step 2: Funding & Project Information"""

    # Override the FK field with our custom one that accepts '__other__'
    funding_agency_obj = FundingAgencyWithOtherChoiceField(
        queryset=FundingAgency.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label='---------',
        label='Funding Agency',
    )

    # Extra fields for creating a new funding agency when "Other" is selected
    new_funding_agency_name = forms.CharField(
        max_length=200, required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter new funding agency name'
        }),
        label='Funding Agency Name',
    )

    new_funding_agency_origin_of_funds = forms.ChoiceField(
        choices=[('', '---------')] + PROJECT_TYPES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Origin of Funds',
    )

    class Meta:
        model = Application
        fields = [
            'has_competitive_funding',
            'project_title', 'project_code', 'funding_agency_obj',
            'subject_area'
        ]
        widgets = {
            'has_competitive_funding': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'project_title': forms.TextInput(attrs={'class': 'form-control'}),
            'project_code': forms.TextInput(attrs={'class': 'form-control'}),
            'subject_area': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'project_title': 'Funded Project Name',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['subject_area'].required = True
        # Append "Other" sentinel to the choices the widget renders
        agency_choices = list(self.fields['funding_agency_obj'].choices)
        agency_choices.append(('__other__', 'Other (enter new)'))
        self.fields['funding_agency_obj'].choices = agency_choices

        # Build JSON map of {agency_id: origin_of_funds} for JavaScript
        origins = {
            str(a.pk): a.origin_of_funds
            for a in FundingAgency.objects.all()
        }
        self.fields['funding_agency_obj'].widget.attrs['data-origins'] = json.dumps(origins)

    def clean(self):
        cleaned_data = super().clean()
        has_funding = cleaned_data.get('has_competitive_funding')

        if not has_funding:
            # Clear funding fields when no competitive funding
            cleaned_data['project_title'] = ''
            cleaned_data['project_code'] = ''
            cleaned_data['funding_agency_obj'] = None
            cleaned_data['project_type'] = ''
        else:
            agency_val = cleaned_data.get('funding_agency_obj')

            if agency_val == FundingAgencyWithOtherChoiceField.OTHER_SENTINEL:
                # "Other (enter new)" — require name and origin of funds
                new_name = cleaned_data.get('new_funding_agency_name', '').strip()
                new_origin = cleaned_data.get('new_funding_agency_origin_of_funds', '')

                if not new_name:
                    self.add_error('new_funding_agency_name', 'Please enter the funding agency name.')
                if not new_origin:
                    self.add_error('new_funding_agency_origin_of_funds', 'Please select the origin of funds.')

                if new_name and new_origin:
                    agency, created = FundingAgency.objects.get_or_create(
                        name=new_name,
                        defaults={'origin_of_funds': new_origin}
                    )
                    if not created and not agency.origin_of_funds:
                        agency.origin_of_funds = new_origin
                        agency.save()
                    cleaned_data['funding_agency_obj'] = agency
                    cleaned_data['project_type'] = agency.origin_of_funds
                else:
                    cleaned_data['funding_agency_obj'] = None

            elif agency_val and hasattr(agency_val, 'origin_of_funds'):
                # Existing agency selected
                if agency_val.origin_of_funds:
                    cleaned_data['project_type'] = agency_val.origin_of_funds
                else:
                    # Agency missing origin_of_funds — require user to provide it
                    new_origin = cleaned_data.get('new_funding_agency_origin_of_funds', '')
                    if not new_origin:
                        self.add_error(
                            'new_funding_agency_origin_of_funds',
                            'This agency is missing its Origin of Funds. Please select one.'
                        )
                    else:
                        agency_val.origin_of_funds = new_origin
                        agency_val.save()
                        cleaned_data['project_type'] = new_origin
            else:
                cleaned_data['project_type'] = ''

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.project_type = self.cleaned_data.get('project_type', '')
        if commit:
            instance.save()
        return instance


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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['service_modality'].required = True
        self.fields['specialization_area'].required = True


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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in self.fields:
            self.fields[field_name].required = True


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

    def __init__(self, *args, **kwargs):
        self._user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # If user has auto_data_consent, pre-check and disable the field
        if self._user and getattr(self._user, 'auto_data_consent', False):
            self.initial['data_consent'] = True
            self.fields['data_consent'].disabled = True

    def clean(self):
        """Validate declarations"""
        cleaned_data = super().clean()

        # If auto-consent, force it (disabled fields don't submit data)
        if self._user and getattr(self._user, 'auto_data_consent', False):
            cleaned_data['data_consent'] = True

        # Data consent is required
        if not cleaned_data.get('data_consent'):
            raise forms.ValidationError(
                "You must consent to data processing to submit your application."
            )

        return cleaned_data


class FeasibilityReviewForm(forms.ModelForm):
    """Feasibility review by node coordinator"""

    DECISION_CHOICES = [
        ('approved', 'Approve - Technically feasible'),
        ('rejected', 'Reject - Not feasible'),
        ('edits_requested', 'Request Edits - Return to applicant for revision'),
    ]

    decision = forms.ChoiceField(
        choices=DECISION_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        label='Feasibility Decision',
        required=True,
    )

    class Meta:
        model = FeasibilityReview
        fields = ['comments']
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
        """Validate that comments are provided for reject and edits_requested."""
        cleaned_data = super().clean()
        decision = cleaned_data.get('decision')
        comments = cleaned_data.get('comments')

        if decision == 'rejected' and not comments:
            raise forms.ValidationError(
                "Please provide comments explaining why the application is not feasible."
            )

        if decision == 'edits_requested' and not comments:
            raise forms.ValidationError(
                "Please provide comments explaining what edits the applicant needs to make."
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
        min_value=0.0,
        max_value=12.0,
        initial=9.0,
        decimal_places=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.5',
            'placeholder': '9.0'
        }),
        help_text="Minimum score for acceptance (0.0-12.0). Applications below this threshold will be rejected. Default: 9.0 (75%)"
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
        if threshold < 0.0 or threshold > 12.0:
            raise forms.ValidationError("Threshold score must be between 0.0 and 12.0")
        return threshold


# =============================================================================
# Phase 6: Node Resolution Forms (Multi-Node Coordination)
# =============================================================================

class NodeResolutionForm(forms.Form):
    """
    Form for node coordinator to resolve an application for their node.

    This form handles the resolution decision only. Equipment hours are
    handled separately through NodeResolutionEquipmentForm.
    """

    RESOLUTION_CHOICES = [
        ('accept', 'Accept - Approve equipment access for this node'),
        ('waitlist', 'Waitlist - Limited capacity at this time'),
        ('reject', 'Reject - Cannot accommodate this request'),
    ]

    resolution = forms.ChoiceField(
        choices=RESOLUTION_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        required=True,
        label='Resolution Decision'
    )

    comments = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 4,
            'class': 'form-control',
            'placeholder': 'Provide reasoning for your decision...'
        }),
        required=False,
        label='Comments'
    )

    def __init__(self, *args, **kwargs):
        """
        Customize form based on application properties.

        If application has competitive funding, remove 'reject' option.
        """
        self.has_competitive_funding = kwargs.pop('has_competitive_funding', False)
        super().__init__(*args, **kwargs)

        # Remove 'reject' choice if has_competitive_funding
        if self.has_competitive_funding:
            self.fields['resolution'].choices = [
                choice for choice in self.RESOLUTION_CHOICES
                if choice[0] != 'reject'
            ]
            self.fields['resolution'].help_text = (
                "This application has competitive funding and cannot be rejected. "
                "You must either accept or waitlist."
            )

    def clean(self):
        """Validate resolution business rules."""
        cleaned_data = super().clean()
        resolution = cleaned_data.get('resolution')

        # Validate: competitive funding cannot be rejected
        if self.has_competitive_funding and resolution == 'reject':
            raise forms.ValidationError(
                "Applications with competitive funding cannot be rejected."
            )

        # Require comments if rejecting
        if resolution == 'reject' and not cleaned_data.get('comments'):
            raise forms.ValidationError(
                "Please provide comments explaining why you are rejecting this application."
            )

        return cleaned_data


class NodeResolutionEquipmentForm(forms.Form):
    """
    Form for setting hours_approved for a single equipment item.

    Used dynamically in the resolution view - one instance per equipment item
    from the node coordinator's node.
    """

    equipment_id = forms.IntegerField(widget=forms.HiddenInput())
    equipment_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control-plaintext', 'readonly': True})
    )
    hours_requested = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control-plaintext', 'readonly': True})
    )
    hours_approved = forms.DecimalField(
        max_digits=6,
        decimal_places=1,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.5',
            'min': '0'
        }),
        label='Hours Approved'
    )

    def __init__(self, *args, **kwargs):
        """Initialize with equipment data."""
        equipment_data = kwargs.pop('equipment_data', None)
        super().__init__(*args, **kwargs)

        if equipment_data:
            self.fields['equipment_id'].initial = equipment_data.get('equipment_id')
            self.fields['equipment_name'].initial = equipment_data.get('equipment_name')
            self.fields['hours_requested'].initial = equipment_data.get('hours_requested')
            # Default hours_approved to hours_requested
            if not self.initial.get('hours_approved'):
                self.fields['hours_approved'].initial = equipment_data.get('hours_requested')


class EquipmentCompletionForm(forms.Form):
    """
    Form for marking equipment access as completed and reporting actual hours used.

    Can be used by either applicants or node coordinators.
    """

    actual_hours_used = forms.DecimalField(
        max_digits=6,
        decimal_places=1,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.5',
            'min': '0'
        }),
        label='Actual Hours Used',
        help_text='Enter the actual number of hours used for this equipment'
    )

    completion_notes = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3,
            'class': 'form-control',
            'placeholder': 'Optional notes about the completed access...'
        }),
        required=False,
        label='Notes (optional)'
    )

    def __init__(self, *args, **kwargs):
        """Initialize with approved hours for reference."""
        self.hours_approved = kwargs.pop('hours_approved', None)
        super().__init__(*args, **kwargs)

        if self.hours_approved:
            self.fields['actual_hours_used'].help_text = (
                f'Approved hours: {self.hours_approved}. '
                'Enter the actual number of hours used.'
            )


# =============================================================================
# PDF Signature Upload Form
# =============================================================================

class SignedPdfUploadForm(forms.Form):
    """
    Form for uploading a signed PDF application.

    Validates:
    - File extension (.pdf only)
    - MIME type (application/pdf)
    - File size (max 5MB)
    - Signature affirmation checkbox (required)
    """

    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB in bytes

    signed_pdf = forms.FileField(
        label='Signed PDF File',
        help_text='Upload your signed PDF (maximum 5MB)',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.pdf,application/pdf'
        })
    )

    signature_affirmation = forms.BooleanField(
        required=True,
        label=(
            'I declare that the uploaded PDF has been signed with a valid '
            'qualified electronic certificate (certificado digital cualificado) '
            'in accordance with eIDAS regulations.'
        ),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    def clean_signed_pdf(self):
        """Validate the uploaded PDF file."""
        uploaded_file = self.cleaned_data.get('signed_pdf')

        if not uploaded_file:
            raise forms.ValidationError("Please select a PDF file to upload.")

        # Check file extension
        if not uploaded_file.name.lower().endswith('.pdf'):
            raise forms.ValidationError("Only PDF files are accepted.")

        # Check MIME type
        content_type = uploaded_file.content_type
        if content_type != 'application/pdf':
            raise forms.ValidationError(
                "The uploaded file is not a valid PDF."
            )

        # Check file size
        if uploaded_file.size > self.MAX_FILE_SIZE:
            raise forms.ValidationError(
                f"File size exceeds the 5MB limit. "
                f"Your file is {uploaded_file.size / (1024*1024):.1f}MB."
            )

        return uploaded_file

    def clean_signature_affirmation(self):
        """Validate signature affirmation is checked."""
        affirmation = self.cleaned_data.get('signature_affirmation')

        if not affirmation:
            raise forms.ValidationError(
                "You must confirm that the PDF has been signed."
            )

        return affirmation
