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

        # Hero slideshow: 3 rotating messages over the imaging photos.
        imgs = [c.hero_image for c in cats if c.hero_image_id][:3]
        calls_url = '/portal/calls/'
        eq_url = ctx['equipment_index'].url if ctx['equipment_index'] else calls_url
        if locale.language_code == 'en':
            messages = [
                {'eyebrow': 'Unique Scientific & Technical Infrastructure (ICTS)',
                 'title': 'Distributed Biomedical Imaging Network',
                 'text': 'Open access to cutting-edge clinical and preclinical biomedical imaging across four Spanish nodes.',
                 'cta': 'Request access', 'url': calls_url},
                {'eyebrow': 'Competitive Open Access',
                 'title': 'Apply for access to our infrastructure',
                 'text': 'Periodic calls give academic and industry researchers access to state-of-the-art imaging.',
                 'cta': 'View calls', 'url': calls_url},
                {'eyebrow': 'Equipment',
                 'title': 'State-of-the-art clinical & preclinical imaging',
                 'text': 'PET-MR, PET-CT, high-field MRI, SPECT and cyclotron radiochemistry.',
                 'cta': 'Explore equipment', 'url': eq_url},
            ]
        else:
            messages = [
                {'eyebrow': 'Infraestructura Científica y Técnica Singular (ICTS)',
                 'title': 'Red Distribuida de Imagen Biomédica',
                 'text': 'Acceso abierto a imagen biomédica clínica y preclínica de vanguardia en cuatro nodos españoles.',
                 'cta': 'Solicitar acceso', 'url': calls_url},
                {'eyebrow': 'Acceso Abierto Competitivo',
                 'title': 'Solicita acceso a nuestra infraestructura',
                 'text': 'Convocatorias periódicas para investigadores académicos y de la industria.',
                 'cta': 'Ver convocatorias', 'url': calls_url},
                {'eyebrow': 'Equipamiento',
                 'title': 'Imagen clínica y preclínica de última generación',
                 'text': 'PET-RM, PET-TC, RM de alto campo, SPECT y radioquímica con ciclotrón.',
                 'cta': 'Ver equipamiento', 'url': eq_url},
            ]
        slides = []
        for i, m in enumerate(messages):
            slide = dict(m)
            slide['image'] = imgs[i] if i < len(imgs) else (imgs[0] if imgs else None)
            slides.append(slide)
        ctx['hero_slides'] = slides
        return ctx
