"""Marketing-site home page model.

Minimal Phase 1 stub. We'll flesh out the hero, news teaser, equipment grid,
etc. in Phase 2/3 — the goal here is just to prove the Wagtail + bilingual
plumbing works end-to-end.

`Page` inherits `TranslatableMixin` from Wagtail 4+, so with
`WAGTAIL_I18N_ENABLED=True` (see redib/settings.py) translation is available
without further model config.
"""
from django.db import models  # noqa: F401  (kept for future fields)

from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField
from wagtail.models import Page


class HomePage(Page):
    """Marketing-site landing page."""

    body = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('body'),
    ]
