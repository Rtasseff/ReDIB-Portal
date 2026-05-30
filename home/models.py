"""Marketing-site home page model.

Phase 2 expands the Phase 1 stub with hero fields (image + heading +
subheading). Real content for news teaser, equipment grid, partner logos,
etc. lands in Phase 3.

`Page` inherits `TranslatableMixin` from Wagtail 4+, so with
`WAGTAIL_I18N_ENABLED=True` (see redib/settings.py) translation is available
without further model config.
"""
from django.db import models

from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.fields import RichTextField
from wagtail.models import Page


class HomePage(Page):
    """Marketing-site landing page."""

    # Hero
    hero_image = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
    )
    hero_heading = models.CharField(max_length=200, blank=True)
    hero_subheading = models.CharField(max_length=500, blank=True)

    # Body
    body = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        MultiFieldPanel(
            [
                FieldPanel('hero_image'),
                FieldPanel('hero_heading'),
                FieldPanel('hero_subheading'),
            ],
            heading='Hero',
        ),
        FieldPanel('body'),
    ]
