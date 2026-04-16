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

    # Extra fields for "Other (create new)" organization. Required only when
    # the user picks the __other__ sentinel; clean() enforces that. ISO2 is
    # intentionally NOT exposed here — leave it blank for self-service entries
    # and a coordinator can fill it later via the admin.
    new_org_name = forms.CharField(
        max_length=255, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Organization name'}),
        label='Organization Name',
    )
    new_org_short_name = forms.CharField(
        max_length=100, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Acronym / short name'}),
        label='Short Name',
    )
    new_org_vat = forms.CharField(
        max_length=50, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'VAT / NIF'}),
        label='VAT / NIF',
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
    new_org_address = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Street address'}),
        label='Address',
    )
    new_org_city = forms.CharField(
        max_length=100, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
        label='City',
    )
    new_org_zip = forms.CharField(
        max_length=20, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Postal code'}),
        label='Postal Code',
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
        self._evaluator_role.areas = ';'.join(selected)
        self._evaluator_role.save(update_fields=['areas'])

    # Fields the user must fill when "Other (create new)" is selected.
    # ISO2 is intentionally absent — see the form-level comment above.
    NEW_ORG_REQUIRED = [
        ('new_org_name', 'organization name'),
        ('new_org_short_name', 'short name / acronym'),
        ('new_org_vat', 'VAT / NIF'),
        ('new_org_type', 'organization type'),
        ('new_org_country', 'country'),
        ('new_org_address', 'address'),
        ('new_org_city', 'city'),
        ('new_org_zip', 'postal code'),
    ]

    def clean(self):
        cleaned_data = super().clean()
        org_val = cleaned_data.get('organization')

        if org_val == OrgWithOtherChoiceField.OTHER_SENTINEL:
            values = {
                key: (cleaned_data.get(key) or '').strip()
                for key, _ in self.NEW_ORG_REQUIRED
            }
            for key, label in self.NEW_ORG_REQUIRED:
                if not values[key]:
                    self.add_error(key, f'Please enter the {label}.')

            if all(values.values()):
                org, _ = Organization.objects.get_or_create(
                    name=values['new_org_name'],
                    defaults={
                        'short_name': values['new_org_short_name'],
                        'vat': values['new_org_vat'],
                        'organization_type': values['new_org_type'],
                        'country': values['new_org_country'],
                        'address': values['new_org_address'],
                        'city': values['new_org_city'],
                        'zip': values['new_org_zip'],
                        # iso2 left blank by design — coordinator fills via admin
                        'iso2': '',
                    },
                )
                cleaned_data['organization'] = org
            else:
                # Validation failed - clear the sentinel so ModelForm doesn't
                # try to save it as the FK value
                cleaned_data['organization'] = None

        return cleaned_data
