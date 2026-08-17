"""
Tests for the rendered user guide page (/help/user-guide/).

`docs/USER_GUIDE.md` is the single source of truth for the end-user guide;
`core.views.user_guide` renders it to HTML at request time (replacing the
static PDF that used to be committed under `static/documents/`). These tests
cover the contract that keeps that arrangement honest:

- the page is public and survives the profile-completion middleware,
- every `](#anchor)` link in the markdown resolves to a real heading id, so
  the hand-written Table of Contents can't rot,
- the navbar points at the page and no longer at the PDF,
- a missing source file fails `manage.py check` (and therefore the deploy)
  instead of 404-ing quietly.
"""

import re
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.checks import Error
from django.test import TestCase, Client
from django.urls import reverse

from core.checks import user_guide_file_check
from core.views import USER_GUIDE_PATH

User = get_user_model()


class UserGuidePageTest(TestCase):
    """The guide renders for everyone, logged in or not."""

    def setUp(self):
        self.client = Client()
        self.url = reverse('core:user_guide')

    def test_url_is_the_expected_path(self):
        """External links are shared by email; the path is part of the contract."""
        self.assertEqual(self.url, '/help/user-guide/')

    def test_anonymous_user_gets_the_guide(self):
        """Public page - first-time evaluators read it before they have an account."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'help/user_guide.html')
        self.assertContains(response, 'ReDIB COA Portal - User Guide')

    def test_markdown_is_rendered_not_escaped(self):
        """The body is real HTML, not a wall of escaped markdown."""
        html = self.client.get(self.url).content.decode()

        self.assertIn('<h2 id="introduction">', html)
        self.assertIn('<table>', html)
        self.assertNotIn('## Introduction', html)

    def test_sidebar_toc_is_present(self):
        """Python-Markdown's toc extension feeds the sticky sidebar."""
        response = self.client.get(self.url)

        self.assertContains(response, 'class="toc"')
        self.assertContains(response, 'On this page')

    def test_incomplete_profile_user_can_still_read_it(self):
        """`/help/` is exempt from ProfileCompletionMiddleware."""
        user = User.objects.create_user(
            email='newbie@example.com',
            password='testpass123',
        )
        self.assertFalse(user.is_profile_complete)
        self.client.force_login(user)

        # Sanity check: an unexempt page does redirect this user.
        redirected = self.client.get(reverse('core:dashboard'))
        self.assertRedirects(redirected, reverse('core:profile'))

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ReDIB COA Portal - User Guide')


class UserGuideAnchorIntegrityTest(TestCase):
    """
    Regression guard for the guide's hand-written Table of Contents.

    Python-Markdown slugifies headings the same way GitHub does, so the
    markdown's `](#anchor)` links work in both places - but only as long as
    nobody renames a heading without fixing the TOC. This test makes that a
    hard failure.
    """

    def test_every_internal_anchor_resolves_to_a_heading(self):
        markdown_text = USER_GUIDE_PATH.read_text(encoding='utf-8')
        html = self.client.get(reverse('core:user_guide')).content.decode()

        linked_anchors = set(re.findall(r'\]\(#([^)]+)\)', markdown_text))
        rendered_ids = set(re.findall(r'id="([^"]+)"', html))

        self.assertTrue(linked_anchors, 'Expected in-page links in USER_GUIDE.md')

        broken = sorted(linked_anchors - rendered_ids)
        self.assertEqual(
            broken, [],
            f'USER_GUIDE.md links to anchors with no matching heading: {broken}'
        )


class UserGuideNavLinkTest(TestCase):
    """"Need help? -> User guide" opens the page, and the PDF is gone."""

    def test_navbar_links_to_the_guide_page(self):
        response = self.client.get(reverse('core:user_guide'))

        self.assertContains(response, f'href="{reverse("core:user_guide")}"')

    def test_no_template_references_the_old_pdf(self):
        base_template = Path(__file__).resolve().parent.parent / 'templates' / 'base.html'
        contents = base_template.read_text(encoding='utf-8')

        self.assertNotIn('documents/user_guide.pdf', contents)
        self.assertIn("{% url 'core:user_guide' %}", contents)

    def test_pdf_is_deleted_from_static(self):
        static_dir = Path(__file__).resolve().parent.parent / 'static'

        self.assertEqual(list(static_dir.glob('**/user_guide.pdf')), [])


class UserGuideSystemCheckTest(TestCase):
    """`core.E001` turns a bad Docker build context into a loud deploy failure."""

    def test_check_passes_when_the_guide_exists(self):
        self.assertEqual(user_guide_file_check(None), [])

    def test_check_errors_when_the_guide_is_missing(self):
        missing = USER_GUIDE_PATH.parent / 'NO_SUCH_GUIDE.md'

        with patch('core.views.USER_GUIDE_PATH', missing):
            errors = user_guide_file_check(None)

        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], Error)
        self.assertEqual(errors[0].id, 'core.E001')
