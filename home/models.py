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

    def get_context(self, request, *args, **kwargs):
        """Aggregator data for the landing page, matching the live redib.net
        layout: a 3-slide imaging carousel, equipment teaser cards, a node
        grid, and the two most recent news posts. All read live from the
        marketing tree in the page's own locale — no duplicated content.
        """
        ctx = super().get_context(request, *args, **kwargs)
        from marketing.models import (
            EquipmentCategoryPage, EquipmentIndexPage,
            NodePage, NodeIndexPage, NewsPage, NewsIndexPage,
        )
        locale = self.locale
        cats = list(
            EquipmentCategoryPage.objects.live()
            .filter(locale=locale).order_by('path')
        )
        ctx['equipment_categories'] = cats
        # Carousel = the area-keyed imaging categories that have a hero image
        # (Clinical / Preclinical / Radiochemistry); the analytics category
        # has no area_key and no hero, so it stays a teaser card only.
        ctx['carousel_categories'] = [c for c in cats if c.area_key and c.hero_image_id]
        ctx['home_nodes'] = list(
            NodePage.objects.live().filter(locale=locale).order_by('path')
        )
        ctx['recent_news'] = list(
            NewsPage.objects.live().filter(locale=locale).order_by('-date')[:3]
        )
        ctx['equipment_index'] = (
            EquipmentIndexPage.objects.live().filter(locale=locale).first()
        )
        ctx['node_index'] = (
            NodeIndexPage.objects.live().filter(locale=locale).first()
        )
        ctx['news_index'] = (
            NewsIndexPage.objects.live().filter(locale=locale).first()
        )
        return ctx
