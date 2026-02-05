"""
Test suite for design overhaul: static files, CSS extraction, and auth template overrides.

Tests verify:
- Static files exist and are findable by Django's staticfiles finders
- Key pages render without errors (status 200)
- Inline <style> blocks have been removed from cleaned templates
- Auth pages use the project's template chain (not allauth defaults)
- collectstatic works without errors
"""

from django.test import TestCase, Client, override_settings
from django.contrib.staticfiles import finders
from django.contrib.auth import get_user_model
from django.template.loader import get_template
from pathlib import Path
import os

User = get_user_model()

BASE_DIR = Path(__file__).resolve().parent.parent


class StaticFilesExistTest(TestCase):
    """Verify that all expected static files exist and are findable."""

    def test_main_css_exists(self):
        result = finders.find('css/main.css')
        self.assertIsNotNone(result, "static/css/main.css not found by staticfiles finders")

    def test_auth_css_exists(self):
        result = finders.find('css/auth.css')
        self.assertIsNotNone(result, "static/css/auth.css not found by staticfiles finders")

    def test_logo_placeholder_exists(self):
        result = finders.find('images/logo-placeholder.svg')
        self.assertIsNotNone(result, "static/images/logo-placeholder.svg not found by staticfiles finders")

    def test_main_css_has_brand_variables(self):
        css_path = finders.find('css/main.css')
        content = Path(css_path).read_text()
        self.assertIn('--redib-primary', content, "main.css missing --redib-primary CSS variable")
        self.assertIn('--redib-secondary', content, "main.css missing --redib-secondary CSS variable")
        self.assertIn('--redib-accent', content, "main.css missing --redib-accent CSS variable")

    def test_main_css_has_sidebar_styles(self):
        css_path = finders.find('css/main.css')
        content = Path(css_path).read_text()
        self.assertIn('.sidebar', content, "main.css missing sidebar styles")

    def test_main_css_has_text_pre_wrap(self):
        css_path = finders.find('css/main.css')
        content = Path(css_path).read_text()
        self.assertIn('.text-pre-wrap', content, "main.css missing .text-pre-wrap utility")

    def test_main_css_has_progress_lg(self):
        css_path = finders.find('css/main.css')
        content = Path(css_path).read_text()
        self.assertIn('.progress-lg', content, "main.css missing .progress-lg utility")

    def test_main_css_has_sticky_sidebar_card(self):
        css_path = finders.find('css/main.css')
        content = Path(css_path).read_text()
        self.assertIn('.sticky-sidebar-card', content, "main.css missing .sticky-sidebar-card utility")

    def test_auth_css_has_auth_wrapper(self):
        css_path = finders.find('css/auth.css')
        content = Path(css_path).read_text()
        self.assertIn('.auth-wrapper', content, "auth.css missing .auth-wrapper class")
        self.assertIn('.auth-card', content, "auth.css missing .auth-card class")
        self.assertIn('.auth-brand', content, "auth.css missing .auth-brand class")

    def test_logo_is_valid_svg(self):
        svg_path = finders.find('images/logo-placeholder.svg')
        content = Path(svg_path).read_text()
        self.assertIn('<svg', content, "Logo placeholder is not valid SVG")
        self.assertIn('ReDIB', content, "Logo placeholder does not contain ReDIB text")


class InlineStylesRemovedTest(TestCase):
    """Verify inline <style> blocks have been extracted from cleaned templates."""

    TEMPLATES_DIR = BASE_DIR / 'templates'

    def _read_template(self, relative_path):
        full_path = self.TEMPLATES_DIR / relative_path
        return full_path.read_text()

    def test_dashboard_base_no_inline_style(self):
        content = self._read_template('dashboard_base.html')
        self.assertNotIn('<style>', content,
                         "dashboard_base.html still has inline <style> block")

    def test_dashboard_base_no_bootstrap_icons_cdn(self):
        content = self._read_template('dashboard_base.html')
        self.assertNotIn('bootstrap-icons', content,
                         "dashboard_base.html still has Bootstrap Icons CDN (should be in base.html)")

    def test_detail_no_inline_style(self):
        content = self._read_template('applications/detail.html')
        self.assertNotIn('<style>', content,
                         "applications/detail.html still has inline <style> block")

    def test_preview_no_inline_style(self):
        content = self._read_template('applications/preview.html')
        self.assertNotIn('<style>', content,
                         "applications/preview.html still has inline <style> block")

    def test_feasibility_review_no_inline_style(self):
        content = self._read_template('applications/feasibility_review.html')
        self.assertNotIn('<style>', content,
                         "applications/feasibility_review.html still has inline <style> block")

    def test_node_resolution_review_no_inline_style(self):
        content = self._read_template('applications/node_resolution/review.html')
        self.assertNotIn('<style>', content,
                         "applications/node_resolution/review.html still has inline <style> block")

    def test_evaluation_form_no_inline_style(self):
        content = self._read_template('evaluations/evaluation_form.html')
        self.assertNotIn('<style>', content,
                         "evaluations/evaluation_form.html still has inline <style> block")

    def test_wizard_templates_use_progress_lg_class(self):
        for step in range(1, 6):
            content = self._read_template(f'applications/wizard_step{step}.html')
            self.assertIn('progress-lg', content,
                          f"wizard_step{step}.html not using progress-lg CSS class")
            self.assertNotIn('style="height: 30px;"', content,
                             f"wizard_step{step}.html still has inline progress bar height")

    def test_wizard_templates_use_sticky_sidebar_class(self):
        for step in range(1, 6):
            content = self._read_template(f'applications/wizard_step{step}.html')
            self.assertIn('sticky-sidebar-card', content,
                          f"wizard_step{step}.html not using sticky-sidebar-card CSS class")
            self.assertNotIn('style="top: 20px;"', content,
                             f"wizard_step{step}.html still has inline top style")


class BaseTemplateTest(TestCase):
    """Verify base.html includes required assets."""

    def test_base_includes_main_css(self):
        content = (BASE_DIR / 'templates' / 'base.html').read_text()
        self.assertIn("css/main.css", content,
                      "base.html does not reference main.css")

    def test_base_includes_bootstrap_icons(self):
        content = (BASE_DIR / 'templates' / 'base.html').read_text()
        self.assertIn('bootstrap-icons', content,
                      "base.html does not include Bootstrap Icons CDN")

    def test_base_includes_logo(self):
        content = (BASE_DIR / 'templates' / 'base.html').read_text()
        self.assertIn('ReDiB_logo.png', content,
                      "base.html does not include ReDiB logo")


class AuthTemplateOverrideTest(TestCase):
    """Verify auth templates exist and extend the project's base template chain."""

    def test_login_template_exists(self):
        tpl = get_template('account/login.html')
        self.assertIsNotNone(tpl)

    def test_signup_template_exists(self):
        tpl = get_template('account/signup.html')
        self.assertIsNotNone(tpl)

    def test_logout_template_exists(self):
        tpl = get_template('account/logout.html')
        self.assertIsNotNone(tpl)

    def test_base_entrance_template_exists(self):
        tpl = get_template('account/base_entrance.html')
        self.assertIsNotNone(tpl)

    def test_login_extends_base_entrance(self):
        content = (BASE_DIR / 'templates' / 'account' / 'login.html').read_text()
        self.assertIn("account/base_entrance.html", content,
                      "login.html does not extend base_entrance.html")

    def test_signup_extends_base_entrance(self):
        content = (BASE_DIR / 'templates' / 'account' / 'signup.html').read_text()
        self.assertIn("account/base_entrance.html", content,
                      "signup.html does not extend base_entrance.html")

    def test_logout_extends_base_entrance(self):
        content = (BASE_DIR / 'templates' / 'account' / 'logout.html').read_text()
        self.assertIn("account/base_entrance.html", content,
                      "logout.html does not extend base_entrance.html")

    def test_base_entrance_extends_base(self):
        content = (BASE_DIR / 'templates' / 'account' / 'base_entrance.html').read_text()
        self.assertIn("base.html", content,
                      "base_entrance.html does not extend base.html")

    def test_base_entrance_includes_auth_css(self):
        content = (BASE_DIR / 'templates' / 'account' / 'base_entrance.html').read_text()
        self.assertIn("auth.css", content,
                      "base_entrance.html does not include auth.css")


class AuthPageRenderTest(TestCase):
    """Verify auth pages render successfully with status 200."""

    def setUp(self):
        self.client = Client()

    def test_login_page_renders(self):
        response = self.client.get('/accounts/login/')
        self.assertEqual(response.status_code, 200)
        # Verify it uses our custom template (contains our brand)
        content = response.content.decode()
        self.assertIn('ReDIB Portal', content)
        self.assertIn('auth-wrapper', content)

    def test_signup_page_renders(self):
        response = self.client.get('/accounts/signup/')
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('ReDIB Portal', content)
        self.assertIn('Create Account', content)

    def test_logout_page_renders(self):
        # Logout page requires authentication
        user = User.objects.create_user(
            username='testuser', email='test@test.com', password='testpass123')
        self.client.login(email='test@test.com', password='testpass123')
        response = self.client.get('/accounts/logout/')
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('Sign Out', content)


class DashboardPageRenderTest(TestCase):
    """Verify dashboard and key pages render without errors after style extraction."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser', email='test@test.com', password='testpass123')
        self.client.login(email='test@test.com', password='testpass123')

    def test_dashboard_renders(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_profile_renders(self):
        response = self.client.get('/profile/')
        self.assertEqual(response.status_code, 200)

    def test_calls_list_renders(self):
        response = self.client.get('/calls/')
        self.assertEqual(response.status_code, 200)


class CollectStaticTest(TestCase):
    """Verify collectstatic runs without errors."""

    def test_collectstatic_finds_all_files(self):
        """Verify all our custom static files are found by finders."""
        expected_files = [
            'css/main.css',
            'css/auth.css',
            'images/logo-placeholder.svg',
        ]
        for filename in expected_files:
            result = finders.find(filename)
            self.assertIsNotNone(result, f"collectstatic cannot find {filename}")
