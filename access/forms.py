"""
Forms for the access app - Publication submission.
"""

from django import forms
from .models import Publication


class PublicationForm(forms.ModelForm):
    """Form for applicants to submit publications."""

    class Meta:
        model = Publication
        fields = [
            'application',
            'title',
            'authors',
            'doi',
            'journal',
            'publication_date',
            'redib_acknowledged',
            'acknowledgment_text',
        ]
        widgets = {
            'application': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full publication title'}),
            'authors': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'List of authors'}),
            'doi': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 10.1234/example'}),
            'journal': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Journal or conference name'}),
            'publication_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'redib_acknowledged': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'acknowledgment_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Copy the acknowledgment text from your publication'}),
        }
        labels = {
            'application': 'Which ReDIB application is this publication related to?',
            'title': 'Publication Title',
            'authors': 'Authors',
            'doi': 'DOI (Digital Object Identifier)',
            'journal': 'Journal/Conference',
            'publication_date': 'Publication Date',
            'redib_acknowledged': 'I confirm that ReDIB is acknowledged in this publication',
            'acknowledgment_text': 'Acknowledgment Text (from publication)',
        }
        help_texts = {
            'redib_acknowledged': 'Required: Publications must acknowledge ReDIB support per regulatory requirements',
            'acknowledgment_text': 'Optional: If you included an acknowledgment, copy it here for verification',
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # All fields are required except the optional acknowledgment text.
        # `redib_acknowledged` required=True forces the checkbox to be ticked
        # (False fails Django's required-boolean validation).
        for name in ('application', 'title', 'authors', 'doi', 'journal',
                     'publication_date', 'redib_acknowledged'):
            self.fields[name].required = True
        self.fields['acknowledgment_text'].required = False

        # Publications can only be reported against completed applications.
        if user:
            from applications.models import Application
            self.fields['application'].queryset = Application.objects.filter(
                applicant=user,
                status='completed',
            ).order_by('-completed_at')
