"""Bootstrap Wagtail for the marketing site.

Idempotent: safe to run repeatedly. Creates the ES + EN locales, an initial
bilingual HomePage pair, and points the default Wagtail Site at the ES
homepage so `curl http://localhost:8000/` renders something end-to-end
without manual admin work.

Phase 3 will layer real content on top of this.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from wagtail.models import Locale, Page, Site

from home.models import HomePage


class Command(BaseCommand):
    help = "Bootstrap Wagtail Site, ES/EN Locales, and the initial HomePage (ES + EN)."

    @transaction.atomic
    def handle(self, *args, **options):
        # 1. Locales
        es, _ = Locale.objects.get_or_create(language_code='es')
        en, _ = Locale.objects.get_or_create(language_code='en')
        self.stdout.write(f"Locales: es={es.id}, en={en.id}")

        # 1b. Remove Wagtail's default welcome page so its 'home' slug doesn't
        # collide with our EN HomePage. Safe: the welcome page is the empty
        # placeholder Wagtail ships with a fresh install. Only delete if it's
        # the generic wagtailcore.Page (not one of our own HomePage rows).
        from django.contrib.contenttypes.models import ContentType
        wagtail_page_ct = ContentType.objects.get(app_label='wagtailcore', model='page')
        welcome = (
            Page.objects
            .filter(depth=2, slug='home', content_type=wagtail_page_ct)
            .first()
        )
        if welcome is not None:
            welcome.delete()
            self.stdout.write("Removed Wagtail default welcome page")

        # 2. HomePage (ES) - create if no ES HomePage exists yet
        home_es = HomePage.objects.filter(locale=es).first()
        if home_es is None:
            # Wagtail's tree root is at depth=1; ordinary pages live below it.
            root = Page.objects.get(depth=1)
            home_es = HomePage(
                title='Inicio',
                slug='inicio',
                locale=es,
                hero_heading='Red de Imagen Biomedica Distribuida',
                hero_subheading='Bienvenido a ReDIB.',
                body='<p>Sitio en construccion.</p>',
            )
            root.add_child(instance=home_es)
            home_es.save_revision().publish()
            self.stdout.write(f"Created HomePage ES (id={home_es.id})")
        else:
            self.stdout.write(f"HomePage ES already exists (id={home_es.id})")

        # 3. Default Site -> point at HomePage ES
        site = Site.objects.filter(is_default_site=True).first()
        if site is None:
            site = Site.objects.create(
                hostname='localhost',
                port=8000,
                site_name='ReDIB',
                root_page=home_es,
                is_default_site=True,
            )
            self.stdout.write(f"Created default Site: {site.hostname}:{site.port} -> page {site.root_page_id}")
        else:
            changed = False
            if site.root_page_id != home_es.id:
                site.root_page = home_es
                changed = True
            if site.hostname != 'localhost':
                site.hostname = 'localhost'
                changed = True
            if site.port != 8000:
                site.port = 8000
                changed = True
            if site.site_name != 'ReDIB':
                site.site_name = 'ReDIB'
                changed = True
            if changed:
                site.save()
            self.stdout.write(f"Site updated: {site.hostname}:{site.port} -> page {site.root_page_id}")

        # 4. EN translation via Wagtail's built-in copy_for_translation.
        #
        # copy_for_translation() places the new page at the same tree parent
        # as the source by default — i.e. a SIBLING of the ES homepage, both
        # under the tree root. The default Site only routes URLs under its
        # `root_page` (the ES homepage), so a sibling EN page is unreachable.
        # To make `/home/` resolve, we move the EN homepage to be a CHILD of
        # the ES homepage. The site URL then becomes `<site_root>/home/`,
        # which under the default `/` site root gives `/home/`.
        home_en = HomePage.objects.filter(
            locale=en, translation_key=home_es.translation_key
        ).first()
        if home_en is None:
            home_en = home_es.copy_for_translation(en)
            home_en.title = 'Home'
            home_en.slug = 'home'
            home_en.hero_heading = 'Distributed Biomedical Imaging Network'
            home_en.hero_subheading = 'Welcome to ReDIB.'
            home_en.body = '<p>Site under construction.</p>'
            home_en.save_revision().publish()
            # Make EN a child of ES so it's reachable via the default site.
            home_en.refresh_from_db()
            if home_en.get_parent().id != home_es.id:
                home_en.move(home_es, pos='last-child')
                home_en.refresh_from_db()
            self.stdout.write(f"Created HomePage EN (id={home_en.id}, url={home_en.url})")
        else:
            # Ensure EN is parented under ES (idempotent self-heal).
            if home_en.get_parent().id != home_es.id:
                home_en.move(home_es, pos='last-child')
                home_en.refresh_from_db()
                self.stdout.write(f"Moved HomePage EN under HomePage ES")
            self.stdout.write(f"HomePage EN already exists (id={home_en.id}, url={home_en.url})")
