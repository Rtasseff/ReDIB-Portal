"""
Forms for the core app.
"""
from django import forms
from .models import User, Organization


class ProfileForm(forms.ModelForm):
    """Form for editing user profile information."""

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone', 'orcid', 'organization']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'orcid': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '0000-0002-1234-5678'}),
            'organization': forms.Select(attrs={'class': 'form-select'}),
        }
