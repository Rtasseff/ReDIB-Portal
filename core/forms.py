"""
Forms for the core app.
"""
from django import forms
from .models import User, Organization


class OrgWithOtherChoiceField(forms.ModelChoiceField):
    """
    A ModelChoiceField that accepts the '__other__' sentinel value as valid,
    bypassing queryset.get() lookup for that value. The form's clean() method
    is responsible for converting '__other__' into a real Organization instance.
    """
    OTHER_SENTINEL = '__other__'

    def to_python(self, value):
        if value == self.OTHER_SENTINEL:
            return self.OTHER_SENTINEL
        return super().to_python(value)

    def validate(self, value):
        if value == self.OTHER_SENTINEL:
            return  # Sentinel is always valid; clean() will replace it
        super().validate(value)


class ProfileForm(forms.ModelForm):
    """Form for editing user profile information."""

    # Override the FK field with our custom one that accepts '__other__'
    organization = OrgWithOtherChoiceField(
        queryset=Organization.objects.all(),
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label='---------',
    )

    # Extra fields for "Other" organization creation
    new_org_name = forms.CharField(
        max_length=255, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Organization name'}),
        label='New Organization Name',
    )
    new_org_type = forms.ChoiceField(
        choices=[('', '---------')] + Organization.ORG_TYPES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Organization Type',
    )
    new_org_country = forms.CharField(
        max_length=100, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Country'}),
        label='Country',
        initial='Spain',
    )

    # Self-service field for evaluators to manage their specialization areas.
    # Pre-populated and saved manually in __init__/save (lives on UserRole, not User).
    EVALUATOR_AREA_CHOICES = [
        ('clinical', 'Clinical'),
        ('preclinical', 'Preclinical'),
        ('radiochemistry', 'Radiochemistry'),
    ]
    evaluator_areas = forms.MultipleChoiceField(
        choices=EVALUATOR_AREA_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False,
        label='Evaluator Specialization Areas',
        help_text='Select all areas you can evaluate.',
    )

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'phone', 'position',
            'orcid', 'organization', 'auto_data_consent',
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'position': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Principal Investigator'}),
            'orcid': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '0000-0002-1234-5678'}),
            'auto_data_consent': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'position': 'Title / Position',
            'auto_data_consent': 'Automatic data consent for applications',
        }
        help_texts = {
            'auto_data_consent': (
                'By checking this box, you consent to the processing of your personal data for all future '
                'application submissions. Your data will be incorporated and processed in the file "ICTS ReDIB USERS", '
                'the purpose of which is to receive and evaluate requests for use of the ReDIB facilities. You may exercise '
                'your rights of access, rectification, deletion and portability before the ReDIB nodes through the procedure '
                'available on the ReDIB website: www.redib.net.'
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make profile fields required (except orcid and auto_data_consent)
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['phone'].required = True
        self.fields['position'].required = True
        self.fields['orcid'].required = False
        self.fields['auto_data_consent'].required = False

        # Append "Other" sentinel to the choices the widget renders.
        # This must happen AFTER super().__init__() so the iterator includes existing orgs.
        org_choices = list(self.fields['organization'].choices)
        org_choices.append(('__other__', 'Other (create new)'))
        self.fields['organization'].choices = org_choices

        # Evaluator areas: only show the field if the user has an evaluator role.
        # Pre-populate from the user's existing UserRole(s).
        self._evaluator_role = None
        if self.instance and self.instance.pk:
            self._evaluator_role = self.instance.roles.filter(
                role='evaluator', is_active=True
            ).first()
        if self._evaluator_role:
            self.initial['evaluator_areas'] = self._evaluator_role.area_list
        else:
            # Hide the field entirely for non-evaluators
            self.fields.pop('evaluator_areas')

    def save_evaluator_areas(self):
        """
        Persist the selected evaluator areas to the user's evaluator UserRole.
        Should be called by the view AFTER form.save(), only if the field is present.
        Does nothing if the user has no evaluator role.
        """
        if not self._evaluator_role:
            return
        selected = self.cleaned_data.get('evaluator_areas', [])
        self._evaluator_role.areas = ','.join(selected)
        self._evaluator_role.save(update_fields=['areas'])

    def clean(self):
        cleaned_data = super().clean()
        org_val = cleaned_data.get('organization')

        if org_val == OrgWithOtherChoiceField.OTHER_SENTINEL:
            new_name = cleaned_data.get('new_org_name', '').strip()
            new_type = cleaned_data.get('new_org_type', '')
            new_country = cleaned_data.get('new_org_country', '').strip()

            if not new_name:
                self.add_error('new_org_name', 'Please enter the organization name.')
            if not new_type:
                self.add_error('new_org_type', 'Please select the organization type.')
            if not new_country:
                self.add_error('new_org_country', 'Please enter the country.')

            if new_name and new_type and new_country:
                org, _ = Organization.objects.get_or_create(
                    name=new_name,
                    defaults={
                        'organization_type': new_type,
                        'country': new_country,
                    }
                )
                cleaned_data['organization'] = org
            else:
                # Validation failed for new org fields - clear the sentinel so
                # ModelForm doesn't try to save it as the FK value
                cleaned_data['organization'] = None

        return cleaned_data
