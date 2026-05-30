"""Template tags for the marketing chrome.

Provides:
- ``{% main_nav %}`` — renders the top navigation from the live children of
  the current locale's HomePage (filtered to ``show_in_menus=True``).
- ``{% lang_switch %}`` — renders the ES/EN language switcher from the current
  page's `get_translations()`.
- ``{% external_links_for slug %}`` — pulls ExternalLink snippets in the
  current locale, optionally filtered by category, for rendering on
  /enlaces-de-interes.

The home page is resolved by walking up the page tree until we hit the
locale's HomePage; this works for every Wagtail page in the marketing tree.
For non-Wagtail pages (e.g. error pages) we fall back to the active locale's
HomePage looked up from the DB.
"""
from django import template
from django.utils import translation

from wagtail.models import Locale

from home.models import HomePage
from marketing.models import ExternalLink


register = template.Library()


def _resolve_homepage(context):
    """Return the HomePage for the current request locale.

    Strategy: prefer the page tree (walk up from context['page'] until we
    find a HomePage). Otherwise look up HomePage by active language code.
    """
    page = context.get('page')
    if page is not None:
        node = page
        while node is not None:
            specific = node.specific
            if isinstance(specific, HomePage):
                return specific
            parent = node.get_parent()
            if parent is None or parent.depth == 1:
                # Reached tree root without finding a HomePage — bail.
                break
            node = parent
    # Fallback: active locale (LANGUAGE_CODE) — works on URLs not served
    # by Wagtail (e.g. the redirect target on /actualidad).
    lang = translation.get_language() or 'es'
    locale = Locale.objects.filter(language_code=lang).first()
    if locale is None:
        locale = Locale.objects.filter(language_code='es').first()
    return HomePage.objects.filter(locale=locale).first()


@register.inclusion_tag('marketing/includes/main_nav.html', takes_context=True)
def main_nav(context):
    home_page = _resolve_homepage(context)
    if home_page is None:
        return {'menu_items': [], 'home_page': None}
    children = (
        home_page.get_children()
        .live()
        .in_menu()
        .specific()
    )
    return {
        'menu_items': children,
        'home_page': home_page,
        'request': context.get('request'),
    }


_LANG_CODES = ('es', 'en')


def _homepage_for(code):
    locale = Locale.objects.filter(language_code=code).first()
    if locale is None:
        return None
    return HomePage.objects.filter(locale=locale).live().first()


@register.inclusion_tag('marketing/includes/lang_switch.html', takes_context=True)
def lang_switch(context):
    """Render the ES/EN switcher.

    For each supported language we surface either the page's own translation,
    if one exists, or the opposite-locale HomePage as a fallback — so the
    switcher is never a dead-end (e.g. on ES-only press items).
    """
    page = context.get('page')
    current_code = translation.get_language() or 'es'
    if page is not None and page.locale:
        current_code = page.locale.language_code

    translated_by_code = {}
    if page is not None:
        for trans in page.get_translations(inclusive=True).live().specific():
            translated_by_code[trans.locale.language_code] = trans

    entries = []
    for code in _LANG_CODES:
        if code in translated_by_code:
            target = translated_by_code[code]
            entries.append({'code': code, 'page': target, 'is_fallback': False})
        else:
            fallback = _homepage_for(code)
            if fallback is not None:
                entries.append({'code': code, 'page': fallback, 'is_fallback': True})

    return {
        'entries': entries,
        'current_code': current_code,
    }


@register.inclusion_tag(
    'marketing/includes/external_links.html', takes_context=True
)
def external_links_for(context, category=None):
    """Render ExternalLink snippets in the current locale.

    Usage:
        {% external_links_for %}                       # all categories
        {% external_links_for 'RESOURCE' %}            # just resource cards
    """
    page = context.get('page')
    locale = page.locale if page is not None else None
    if locale is None:
        lang = translation.get_language() or 'es'
        locale = Locale.objects.filter(language_code=lang).first()

    qs = ExternalLink.objects.filter(locale=locale)
    if category:
        qs = qs.filter(category=category)
    qs = qs.order_by('category', 'order', 'title')
    return {'links': qs}
