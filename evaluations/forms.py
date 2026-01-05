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
            # Category 1: Scientific and Technical Relevance
            'score_quality_originality',
            'score_methodology_design',
            'score_expected_contributions',
            # Category 2: Timeliness and Impact
            'score_knowledge_advancement',
            'score_social_economic_impact',
            'score_exploitation_dissemination',
            # Recommendation and Comments
            'recommendation',
            'comments'
        ]

        widgets = {
            'score_quality_originality': forms.RadioSelect(
                choices=[(i, str(i)) for i in range(0, 3)],
                attrs={'class': 'form-check-input'}
            ),
            'score_methodology_design': forms.RadioSelect(
                choices=[(i, str(i)) for i in range(0, 3)],
                attrs={'class': 'form-check-input'}
            ),
            'score_expected_contributions': forms.RadioSelect(
                choices=[(i, str(i)) for i in range(0, 3)],
                attrs={'class': 'form-check-input'}
            ),
            'score_knowledge_advancement': forms.RadioSelect(
                choices=[(i, str(i)) for i in range(0, 3)],
                attrs={'class': 'form-check-input'}
            ),
            'score_social_economic_impact': forms.RadioSelect(
                choices=[(i, str(i)) for i in range(0, 3)],
                attrs={'class': 'form-check-input'}
            ),
            'score_exploitation_dissemination': forms.RadioSelect(
                choices=[(i, str(i)) for i in range(0, 3)],
                attrs={'class': 'form-check-input'}
            ),
            'recommendation': forms.RadioSelect(
                choices=Evaluation.RECOMMENDATION_CHOICES,
                attrs={'class': 'form-check-input'}
            ),
            'comments': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': 'Please provide your detailed evaluation comments...'
            })
        }

        labels = {
            'score_quality_originality': 'Quality and originality of the project and research plan',
            'score_methodology_design': 'Suitability of methodology, design, and work plan to the objectives of the proposal',
            'score_expected_contributions': 'Expected scientific–technical contributions arising from the proposal',
            'score_knowledge_advancement': 'Contribution of the research to the advancement of knowledge',
            'score_social_economic_impact': 'Potential social, economic and/or industrial impact of the expected results',
            'score_exploitation_dissemination': 'Opportunity for exploitation, translation and/or dissemination of the expected results',
            'recommendation': 'Access Decision',
            'comments': 'Comments (optional)'
        }

        # Text help stubs for each score value for each criterion
        help_texts = {
            'score_quality_originality': '',  # Will be shown inline in template
            'score_methodology_design': '',
            'score_expected_contributions': '',
            'score_knowledge_advancement': '',
            'score_social_economic_impact': '',
            'score_exploitation_dissemination': '',
            'recommendation': '',
            'comments': 'Provide detailed feedback on your evaluation (optional)'
        }

    # Text help stubs for displaying in template
    SCORE_HELP_TEXTS = {
        'score_quality_originality': {
            0: 'The project presented has acceptable quality and originality',
            1: 'The project presented has good quality and originality',
            2: 'The project presented stands out for its excellent quality and originality'
        },
        'score_methodology_design': {
            0: 'No experimental design has been presented, or it is considered inadequate',
            1: 'The methodology and work plan are considered acceptable or good',
            2: 'The experimental design is carefully developed and is highly suitable for the objectives'
        },
        'score_expected_contributions': {
            0: 'The proposal does not mention expectations for publication/dissemination of results',
            1: 'The application presents well-founded expectations of future contributions arising from the proposal',
            2: 'The proposal presents well-founded expectations of contributions derived from the requested ICTS access, and commits to documenting it'
        },
        'score_knowledge_advancement': {
            0: 'The application does not justify or mention an eventual contribution to advancing knowledge, or any innovative contribution',
            1: 'The application provides well-founded expectations of advances in knowledge or innovations within the scope of the proposal',
            2: 'The application fully justifies its timeliness and impact through the advancement of knowledge and innovation that will result from the planned studies'
        },
        'score_social_economic_impact': {
            0: 'The application provides no arguments regarding possible social, economic, or industrial relevance of the expected results',
            1: 'The application analyzes possible social, economic, or industrial repercussions of some significance',
            2: 'The application argues in detail the social, economic, and/or industrial importance/significance the expected results will have'
        },
        'score_exploitation_dissemination': {
            0: 'No criteria of timeliness or impact are mentioned regarding advancement of knowledge or in the translational/applied arena',
            1: 'The application generates well-founded expectations of being able to address timely questions of exploitation, translation, or dissemination of results',
            2: 'The application is convincing regarding generating answers to scientific–technical questions of undeniable timeliness, impact, and/or application'
        }
    }

    RECOMMENDATION_HELP_TEXTS = {
        'approved': 'APPROVED because it is based on a Research Project funded through competitive calls by a European or national R&D administration or funding agency, or because, in this evaluator\'s judgment, it meets criteria of ACCEPTABLE SCIENTIFIC–TECHNICAL QUALITY AND RELEVANCE.',
        'denied': 'DENIED because it is not based on a Research Project funded through competitive calls by a European or national R&D administration or funding agency, and because, in this evaluator\'s judgment, it does not meet criteria of ACCEPTABLE SCIENTIFIC–TECHNICAL QUALITY AND RELEVANCE.'
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Make all score fields required
        for field in ['score_quality_originality', 'score_methodology_design',
                      'score_expected_contributions', 'score_knowledge_advancement',
                      'score_social_economic_impact', 'score_exploitation_dissemination']:
            self.fields[field].required = True

        # Make recommendation required
        self.fields['recommendation'].required = True

        # Comments are optional
        self.fields['comments'].required = False

    def clean(self):
        """Validate that all scores and recommendation are provided"""
        cleaned_data = super().clean()

        # Check all scores are present
        scores = [
            cleaned_data.get('score_quality_originality'),
            cleaned_data.get('score_methodology_design'),
            cleaned_data.get('score_expected_contributions'),
            cleaned_data.get('score_knowledge_advancement'),
            cleaned_data.get('score_social_economic_impact'),
            cleaned_data.get('score_exploitation_dissemination')
        ]

        if not all(score is not None for score in scores):
            raise forms.ValidationError('All evaluation scores are required.')

        # Validate range (redundant with model validators, but good practice)
        for score in scores:
            if score is not None and (score < 0 or score > 2):
                raise forms.ValidationError('Scores must be between 0 and 2.')

        # Check recommendation is provided
        if not cleaned_data.get('recommendation'):
            raise forms.ValidationError('A recommendation (Approved/Denied) is required.')

        return cleaned_data
