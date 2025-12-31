"""
Forms for evaluations app - Phase 5: Evaluation Submission
"""

from django import forms
from .models import Evaluation


class EvaluationForm(forms.ModelForm):
    """Form for evaluators to submit scores and comments on applications"""

    class Meta:
        model = Evaluation
        fields = [
            'score_relevance',
            'score_methodology',
            'score_contributions',
            'score_impact',
            'score_opportunity',
            'comments'
        ]

        widgets = {
            'score_relevance': forms.RadioSelect(
                choices=[(i, str(i)) for i in range(1, 6)],
                attrs={'class': 'form-check-input'}
            ),
            'score_methodology': forms.RadioSelect(
                choices=[(i, str(i)) for i in range(1, 6)],
                attrs={'class': 'form-check-input'}
            ),
            'score_contributions': forms.RadioSelect(
                choices=[(i, str(i)) for i in range(1, 6)],
                attrs={'class': 'form-check-input'}
            ),
            'score_impact': forms.RadioSelect(
                choices=[(i, str(i)) for i in range(1, 6)],
                attrs={'class': 'form-check-input'}
            ),
            'score_opportunity': forms.RadioSelect(
                choices=[(i, str(i)) for i in range(1, 6)],
                attrs={'class': 'form-check-input'}
            ),
            'comments': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': 'Please provide your detailed evaluation comments...'
            })
        }

        labels = {
            'score_relevance': 'Scientific Relevance and Originality',
            'score_methodology': 'Methodology and Experimental Design',
            'score_contributions': 'Expected Contributions and Results',
            'score_impact': 'Impact and Strengths',
            'score_opportunity': 'Opportunity Criteria',
            'comments': 'Evaluation Comments'
        }

        help_texts = {
            'score_relevance': 'Rate the scientific relevance and originality of the proposal (1=Poor, 5=Excellent)',
            'score_methodology': 'Rate the quality of the methodology and experimental design (1=Poor, 5=Excellent)',
            'score_contributions': 'Rate the expected contributions and anticipated results (1=Poor, 5=Excellent)',
            'score_impact': 'Rate the potential impact and strengths of the project (1=Poor, 5=Excellent)',
            'score_opportunity': 'Rate how well the project meets the opportunity criteria (1=Poor, 5=Excellent)',
            'comments': 'Provide detailed feedback on your evaluation (optional but recommended)'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Make all score fields required
        for field in ['score_relevance', 'score_methodology', 'score_contributions',
                      'score_impact', 'score_opportunity']:
            self.fields[field].required = True

        # Comments are optional but recommended
        self.fields['comments'].required = False

    def clean(self):
        """Validate that all scores are provided"""
        cleaned_data = super().clean()

        # Check all scores are present
        scores = [
            cleaned_data.get('score_relevance'),
            cleaned_data.get('score_methodology'),
            cleaned_data.get('score_contributions'),
            cleaned_data.get('score_impact'),
            cleaned_data.get('score_opportunity')
        ]

        if not all(scores):
            raise forms.ValidationError('All evaluation scores are required.')

        # Validate range (redundant with model validators, but good practice)
        for score in scores:
            if score and (score < 1 or score > 5):
                raise forms.ValidationError('Scores must be between 1 and 5.')

        return cleaned_data
