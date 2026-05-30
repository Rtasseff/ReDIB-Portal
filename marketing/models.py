"""Marketing-site page types and snippets.

Phase 2: defines all page types and snippets the inventory implies, with
stub templates. Content for real pages lands in Phase 3.

Equipment and Nodes pages use a LIVE QUERY pattern against the portal's
`core.Node` / `core.Equipment` models — we never duplicate that data
into Wagtail. The Wagtail page provides the editable intro/body chrome.
"""
from datetime import date

from django.core.paginator import Paginator
from django.db import models

from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.fields import RichTextField
from wagtail.models import Page, TranslatableMixin
from wagtail.snippets.models import register_snippet


# ---------------------------------------------------------------------------
# Generic content page
# ---------------------------------------------------------------------------

class StandardPage(Page):
    """Generic content page for About, Legal, /enlaces-de-interes, etc."""

    hero_image = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
    )
    intro = models.CharField(max_length=500, blank=True)
    body = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('hero_image'),
        FieldPanel('intro'),
        FieldPanel('body'),
    ]


# ---------------------------------------------------------------------------
# News
# ---------------------------------------------------------------------------

class NewsIndexPage(Page):
    """Listing parent for NewsPage children."""

    intro = models.CharField(max_length=500, blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('intro'),
    ]

    subpage_types = ['marketing.NewsPage']

    def get_context(self, request, *args, **kwargs):
        ctx = super().get_context(request, *args, **kwargs)
        news_qs = (
            NewsPage.objects.child_of(self).live().order_by('-date')
        )
        paginator = Paginator(news_qs, 12)
        page_number = request.GET.get('page')
        ctx['news_posts'] = paginator.get_page(page_number)
        return ctx


class NewsPage(Page):
    """A single news article."""

    date = models.DateField(default=date.today)
    hero_image = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
    )
    intro = models.CharField(max_length=500, blank=True)
    body = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('date'),
        FieldPanel('hero_image'),
        FieldPanel('intro'),
        FieldPanel('body'),
    ]

    parent_page_types = ['marketing.NewsIndexPage']


# ---------------------------------------------------------------------------
# Press
# ---------------------------------------------------------------------------

class PressIndexPage(Page):
    """Listing parent for PressItemPage children."""

    intro = models.CharField(max_length=500, blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('intro'),
    ]

    subpage_types = ['marketing.PressItemPage']

    def get_context(self, request, *args, **kwargs):
        ctx = super().get_context(request, *args, **kwargs)
        press_qs = (
            PressItemPage.objects.child_of(self).live().order_by('-date')
        )
        paginator = Paginator(press_qs, 12)
        page_number = request.GET.get('page')
        ctx['press_items'] = paginator.get_page(page_number)
        return ctx


class PressItemPage(Page):
    """A press clipping or internal press post.

    `external_url` is for outside-the-site press clippings; internal posts
    leave it blank and use `body` for content.
    """

    date = models.DateField(default=date.today)
    outlet = models.CharField(max_length=200, blank=True, help_text='e.g. "El Pais"')
    external_url = models.URLField(blank=True, help_text='Link to the clipping on the outlet site.')
    intro = models.CharField(max_length=500, blank=True)
    body = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('date'),
        FieldPanel('outlet'),
        FieldPanel('external_url'),
        FieldPanel('intro'),
        FieldPanel('body'),
    ]

    parent_page_types = ['marketing.PressIndexPage']


# ---------------------------------------------------------------------------
# Team
# ---------------------------------------------------------------------------

class TeamPage(Page):
    """Equipo / team page - groups Person snippets by `group`."""

    intro = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('intro'),
    ]

    def get_context(self, request, *args, **kwargs):
        ctx = super().get_context(request, *args, **kwargs)
        # Pull all Person snippets in the matching locale; the queryset is
        # ordered by group / order / name (model Meta) so iteration is stable.
        people = list(
            Person.objects
            .filter(locale=self.locale)
            .select_related('photo')
            .order_by('group', 'order', 'name')
        )
        # Render groups in a canonical Coordination → Committee → Advisory →
        # Management order regardless of how they sort alphabetically.
        groups_order = [
            Person.COORDINATOR,
            Person.COMMITTEE,
            Person.ADVISORY,
            Person.MANAGEMENT,
        ]
        people_by_group = {
            g: [p for p in people if p.group == g] for g in groups_order
        }
        ctx['people_by_group'] = people_by_group
        ctx['group_choices'] = Person.GROUP_CHOICES
        return ctx


# ---------------------------------------------------------------------------
# Nodes (live-query pattern against core.Node / core.Equipment)
# ---------------------------------------------------------------------------

class NodeIndexPage(Page):
    """Overview parent for the 4 imaging nodes."""

    intro = models.CharField(max_length=500, blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('intro'),
    ]

    subpage_types = ['marketing.NodePage']

    def get_context(self, request, *args, **kwargs):
        ctx = super().get_context(request, *args, **kwargs)
        ctx['node_pages'] = (
            NodePage.objects.child_of(self).live().order_by('title')
        )
        return ctx


class NodePage(Page):
    """One per imaging node.

    Wagtail page provides editable intro/body/contact/etc.; equipment list
    on the rendered page comes live from `related_core_node.equipment.filter(...)`.
    """

    hero_image = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
    )
    intro = models.CharField(max_length=500, blank=True)
    body = RichTextField(blank=True)
    location_text = models.CharField(
        max_length=500,
        blank=True,
        help_text='Plain-text address / location. Maps are not embedded.',
    )
    contact_info = RichTextField(blank=True)
    related_core_node = models.ForeignKey(
        'core.Node',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        help_text='Portal Node row used for live equipment lookup.',
    )

    content_panels = Page.content_panels + [
        FieldPanel('hero_image'),
        FieldPanel('intro'),
        FieldPanel('body'),
        MultiFieldPanel(
            [
                FieldPanel('location_text'),
                FieldPanel('contact_info'),
            ],
            heading='Location & contact',
        ),
        FieldPanel('related_core_node'),
    ]

    parent_page_types = ['marketing.NodeIndexPage']


# ---------------------------------------------------------------------------
# Equipment (live-query pattern against core.Equipment)
# ---------------------------------------------------------------------------

class EquipmentIndexPage(Page):
    """`/equipamiento` overview - lists category pages."""

    intro = models.CharField(max_length=500, blank=True)
    body = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('intro'),
        FieldPanel('body'),
    ]

    subpage_types = ['marketing.EquipmentCategoryPage']

    def get_context(self, request, *args, **kwargs):
        ctx = super().get_context(request, *args, **kwargs)
        ctx['category_pages'] = (
            EquipmentCategoryPage.objects.child_of(self).live().order_by('title')
        )
        return ctx


class EquipmentCategoryPage(Page):
    """One per equipment category.

    Inventory groups equipment into "Imagen Clinica", "Imagen Preclinica",
    "Analisis", "Radioquimica". The portal's `core.Equipment` model carries
    a per-equipment `area` field with values clinical/preclinical/radiochemistry
    that we use to filter. We pick by `area_key` (matching `core.Equipment.area`).

    Pages whose subject is "Analisis" (image analytics) don't map cleanly to
    any single Equipment row in the portal today - those pages can be created
    with `area_key=''` and will render purely editable content via `body`.
    """

    AREA_CHOICES = [
        ('clinical', 'Clinical'),
        ('preclinical', 'Preclinical'),
        ('radiochemistry', 'Radiochemistry'),
        ('', 'No live equipment query'),
    ]

    intro = models.CharField(max_length=500, blank=True)
    body = RichTextField(blank=True)
    area_key = models.CharField(
        max_length=20,
        blank=True,
        choices=AREA_CHOICES,
        help_text='Live-query filter against core.Equipment.area. Blank = no query.',
    )

    content_panels = Page.content_panels + [
        FieldPanel('intro'),
        FieldPanel('area_key'),
        FieldPanel('body'),
    ]

    parent_page_types = ['marketing.EquipmentIndexPage']

    def get_context(self, request, *args, **kwargs):
        ctx = super().get_context(request, *args, **kwargs)
        from core.models import Equipment
        if self.area_key:
            ctx['equipment_items'] = (
                Equipment.objects
                .filter(area=self.area_key, is_active=True)
                .select_related('node', 'node__organization')
                .order_by('node__code', 'name')
            )
        else:
            ctx['equipment_items'] = Equipment.objects.none()
        return ctx


# ---------------------------------------------------------------------------
# Access (overview only - /convocatorias and /solicitud-de-acceso live in
# the portal app and are explicitly out of scope here)
# ---------------------------------------------------------------------------

class AccessIndexPage(Page):
    """Overview page for /es-acceso. Links out to the portal for actual flows."""

    intro = models.CharField(max_length=500, blank=True)
    body = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('intro'),
        FieldPanel('body'),
    ]


# ---------------------------------------------------------------------------
# Pricing
# ---------------------------------------------------------------------------

class PricingPage(Page):
    """/tarifas. Minimal Phase-2 shape - structured pricing table is deferred."""

    intro = models.CharField(max_length=500, blank=True)
    body = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('intro'),
        FieldPanel('body'),
    ]


# ---------------------------------------------------------------------------
# Contact (no form yet)
# ---------------------------------------------------------------------------

class ContactPage(Page):
    """Informational contact page. No form yet - Phase 3+."""

    intro = models.CharField(max_length=500, blank=True)
    contact_details = RichTextField(
        blank=True,
        help_text='Address, email, phone, etc.',
    )

    content_panels = Page.content_panels + [
        FieldPanel('intro'),
        FieldPanel('contact_details'),
    ]


# ===========================================================================
# Snippets
# ===========================================================================

@register_snippet
class Person(TranslatableMixin, models.Model):
    """Team member. Used by TeamPage; translatable via wagtail-localize."""

    COORDINATOR = 'COORDINATOR'
    COMMITTEE = 'COMMITTEE'
    ADVISORY = 'ADVISORY'
    MANAGEMENT = 'MANAGEMENT'
    GROUP_CHOICES = [
        (COORDINATOR, 'Coordinacion'),
        (COMMITTEE, 'Comite'),
        (ADVISORY, 'Comite asesor'),
        (MANAGEMENT, 'Gestion'),
    ]

    name = models.CharField(max_length=200)
    role = models.CharField(max_length=200, help_text='e.g. "Coordinador"')
    group = models.CharField(max_length=20, choices=GROUP_CHOICES)
    affiliation = models.CharField(max_length=200, blank=True)
    photo = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
    )
    bio = RichTextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    panels = [
        FieldPanel('name'),
        FieldPanel('role'),
        FieldPanel('group'),
        FieldPanel('affiliation'),
        FieldPanel('photo'),
        FieldPanel('bio'),
        FieldPanel('order'),
    ]

    class Meta(TranslatableMixin.Meta):
        ordering = ['group', 'order', 'name']
        verbose_name = 'Person'
        verbose_name_plural = 'People'

    def __str__(self):
        return self.name


@register_snippet
class ExternalLink(TranslatableMixin, models.Model):
    """External / partner link. Used by /enlaces-de-interes plus elsewhere."""

    PARTNER = 'PARTNER'
    RESOURCE = 'RESOURCE'
    INSTITUTIONAL = 'INSTITUTIONAL'
    CATEGORY_CHOICES = [
        (PARTNER, 'Partner'),
        (RESOURCE, 'Resource'),
        (INSTITUTIONAL, 'Institutional'),
    ]

    title = models.CharField(max_length=200)
    url = models.URLField()
    description = models.CharField(max_length=500, blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    order = models.PositiveIntegerField(default=0)

    panels = [
        FieldPanel('title'),
        FieldPanel('url'),
        FieldPanel('description'),
        FieldPanel('category'),
        FieldPanel('order'),
    ]

    class Meta(TranslatableMixin.Meta):
        ordering = ['category', 'order', 'title']
        verbose_name = 'External link'
        verbose_name_plural = 'External links'

    def __str__(self):
        return self.title
