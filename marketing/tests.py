"""Regression tests for the marketing site.

Intentionally narrow — these guard against bug classes that have actually
shipped, not exhaustive coverage of every page:

1. Stray Django template syntax leaking into rendered responses. Multi-line
   ``{# ... #}`` comments are NOT stripped by Django (the comment syntax is
   single-line); they render verbatim into the HTML. This bit us in Phase 4.5
   and again immediately after, in main_nav.html. Asserting absence of ``{#``
   and ``#}`` on every key URL prevents recurrence.
"""
import re

from django.core.management import call_command
from django.test import TestCase


# Patterns that should never appear in a rendered HTML response.
# {# and #} are unambiguous template-syntax leaks; {% %} and {{ }} are
# deliberately NOT checked because they may legitimately appear inside
# <code>, <pre>, or escaped JS strings in future content.
LEAK_PATTERNS = [r'\{#', r'#\}']
LEAK_RE = re.compile('|'.join(LEAK_PATTERNS))


class MarketingTemplateLeakTests(TestCase):
    """Every marketing page must render with no unstripped template syntax."""

    @classmethod
    def setUpTestData(cls):
        # Wagtail Site + Locales + bilingual HomePage + section pages so
        # the URLs we test resolve to real pages.
        call_command('marketing_init', verbosity=0)
        call_command(
            'populate_static_pages', verbosity=0, skip_document_download=True
        )

    def _assert_no_leaks(self, url):
        response = self.client.get(url)
        self.assertEqual(
            response.status_code, 200,
            f"{url} returned HTTP {response.status_code}, expected 200",
        )
        body = response.content.decode('utf-8', errors='replace')
        leak = LEAK_RE.search(body)
        if leak:
            start = max(leak.start() - 40, 0)
            end = min(leak.end() + 40, len(body))
            context = body[start:end].replace('\n', '\\n')
            self.fail(
                f"Template syntax leaked into {url} response near offset "
                f"{leak.start()}: ...{context!r}..."
            )

    def test_marketing_pages_have_no_template_syntax_leaks(self):
        """Walk every page populated by populate_static_pages, both locales.

        Catches the {# #} leak class on whichever shared partial introduced
        it (marketing_base.html, main_nav.html, lang_switch.html, the
        page-type templates, etc.) because every marketing page renders
        the full chrome.
        """
        urls = [
            # HomePage
            '/', '/en/',
            # StandardPage / AccessIndex / ContactPage / PricingPage section parents
            '/quienes-somos/', '/en/about-us/',
            '/es-acceso/', '/en/en-access/',
            '/equipamiento/', '/en/equipment/',
            '/equipo/', '/en/team/',
            '/nodos/', '/en/nodes/',
            '/noticias/', '/en/news/',
            '/prensa/', '/en/press/',
            '/tarifas/', '/en/rates/',
            '/contacto/', '/en/contact/',
            # show_in_menus=False footer pages
            '/enlaces-de-interes/', '/en/links-of-interest/',
            '/aviso-legal/', '/en/legal-notice/',
            # Phase 5b deferred-inventory pages
            '/documentacion/', '/en/documentation/',
            '/costes-de-acceso/', '/en/access-cost/',
            '/politica-de-privacidad-y-cookies/',
            '/en/privacy-policy-and-cookies/',
        ]
        for url in urls:
            with self.subTest(url=url):
                self._assert_no_leaks(url)


import re


class MainNavTests(TestCase):
    """Top nav IA: News+Press are one 'Actualidad' item (→ /noticias/),
    and Prensa + Tarifas are dropped from the menu (folded into the
    Actualidad feed and the Equipment section respectively)."""

    @classmethod
    def setUpTestData(cls):
        call_command('marketing_init', verbosity=0)
        call_command(
            'populate_static_pages', verbosity=0, skip_document_download=True
        )

    def _nav(self, url):
        body = self.client.get(url).content.decode('utf-8')
        m = re.search(r'<ul class="navbar-nav">(.*?)</ul>', body, re.S)
        self.assertIsNotNone(m, f"navbar-nav not found on {url}")
        return m.group(1)

    def test_es_nav(self):
        nav = self._nav('/')
        self.assertIn('href="/noticias/"', nav)
        self.assertIn('Actualidad', nav)
        self.assertNotIn('href="/prensa/"', nav)   # folded into Actualidad
        self.assertNotIn('href="/tarifas/"', nav)  # moved under Equipamiento

    def test_en_nav(self):
        nav = self._nav('/en/')
        self.assertIn('href="/en/news/"', nav)
        self.assertNotIn('href="/en/press/"', nav)
        self.assertNotIn('href="/en/rates/"', nav)
