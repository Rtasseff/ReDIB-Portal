"""Populate the Team / Equipo page with the 14 people (Phase 3b).

Idempotent: safe to run repeatedly.

For each person:
  1. Download the headshot photo into media/marketing/team/<slug>.<ext> (if not
     already present) and create a Wagtail `Image` snippet (matched by title).
     Network failures are logged and skipped — the Person record is still
     created without a photo.
  2. Create the ES `Person` snippet (locale=es) with ES role / bio.
  3. Create the EN `Person` snippet (locale=en) linked via the shared
     `translation_key` (matches the pattern used in Phase 3a for
     `ExternalLink` snippets — `Person` is a TranslatableMixin snippet,
     not a Page, so we don't use `copy_for_translation`).

Names and institution affiliations do NOT translate; roles do.
"""
import mimetypes
import os
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from wagtail.images import get_image_model
from wagtail.models import Locale

from marketing.models import Person


# ---------------------------------------------------------------------------
# Roster — 14 people drawn from docs/marketing/site-inventory.md (Equipo
# section) and docs/marketing/assets-manifest.md (Team headshots table).
# Roles in ES come from the live site; EN roles are direct translations.
# ---------------------------------------------------------------------------

ROSTER = [
    # --- Coordinator (1) ---
    {
        'name': 'Jesús Ruiz-Cabello Osuna',
        'role_es': 'Coordinador',
        'role_en': 'Coordinator',
        'group': Person.COORDINATOR,
        'affiliation': 'CIC biomaGUNE',
        'photo_url': 'https://www.redib.net/upload/secciones-publicas/'
                     'jrc-biomagune_recorte_foto.jpeg',
        'order': 0,
    },

    # --- Coordination Committee (4) ---
    {
        'name': 'José Luis Izquierdo',
        'role_es': 'Vocal',
        'role_en': 'Member',
        'group': Person.COMMITTEE,
        'affiliation': 'BioImaC',
        'photo_url': 'https://www.redib.net/upload/secciones-publicas/'
                     'jose-luiz-izquierdo_foto.jpg',
        'order': 0,
    },
    {
        'name': 'Borja Ibáñez Cabeza',
        'role_es': 'Vocal',
        'role_en': 'Member',
        'group': Person.COMMITTEE,
        'affiliation': 'TRIMA @ CNIC',
        'photo_url': 'https://www.redib.net/upload/secciones-publicas/'
                     'borja-ibanez_foto.jpg',
        'order': 10,
    },
    {
        'name': 'Gonzalo Pizarro Sánchez',
        'role_es': 'Vocal',
        'role_en': 'Member',
        'group': Person.COMMITTEE,
        'affiliation': 'TRIMA @ CNIC',
        'photo_url': 'https://www.redib.net/upload/secciones-publicas/'
                     'foto-gonzalo-olympia-2_foto.jpg',
        'order': 20,
    },
    {
        'name': 'Luis Martí-Bonmatí',
        'role_es': 'Vocal',
        'role_en': 'Member',
        'group': Person.COMMITTEE,
        'affiliation': 'Imaging La Fe',
        'photo_url': 'https://www.redib.net/upload/secciones-publicas/'
                     'luis-marti-bonmati-2_foto.jpg',
        'order': 30,
    },

    # --- Scientific-Technical Advisory Committee (6) ---
    {
        'name': 'Noam Shemesh',
        'role_es': 'Vocal',
        'role_en': 'Member',
        'group': Person.ADVISORY,
        'affiliation': 'Champalimaud, Lisboa',
        'photo_url': 'https://www.redib.net/upload/secciones-publicas/'
                     'noam-shemesh-squared-for-web_foto.jpg',
        'order': 0,
    },
    {
        'name': 'Irene Marco Rius',
        'role_es': 'Vocal',
        'role_en': 'Member',
        'group': Person.ADVISORY,
        'affiliation': 'IBEC, Barcelona',
        'photo_url': 'https://www.redib.net/upload/secciones-publicas/'
                     'profile-picture-imarco-2025-cropped_foto.jpeg',
        'order': 10,
    },
    {
        'name': 'Juan José Vaquero',
        'role_es': 'Vocal',
        'role_en': 'Member',
        'group': Person.ADVISORY,
        'affiliation': 'UC3M, Madrid',
        'photo_url': 'https://www.redib.net/upload/secciones-publicas/'
                     'juan-jose-vaquero_foto.png',
        'order': 20,
    },
    {
        'name': 'Eduardo Fraile Moreno',
        'role_es': 'Vocal',
        'role_en': 'Member',
        'group': Person.ADVISORY,
        'affiliation': 'Hospital San Francisco de Asís',
        'photo_url': 'https://www.redib.net/upload/secciones-publicas/'
                     'foto-visado_foto.jpg',
        'order': 30,
    },
    {
        'name': 'Lluis Donoso Bach',
        'role_es': 'Vocal',
        'role_en': 'Member',
        'group': Person.ADVISORY,
        'affiliation': 'Hospital Clínic, Barcelona',
        'photo_url': 'https://www.redib.net/upload/secciones-publicas/'
                     'thumbnail-image0_foto.jpg',
        'order': 40,
    },
    {
        'name': 'Jeff Bulte',
        'role_es': 'Vocal',
        'role_en': 'Member',
        'group': Person.ADVISORY,
        'affiliation': 'Johns Hopkins',
        'photo_url': 'https://www.redib.net/upload/secciones-publicas/'
                     'bulte_foto.jpg',
        'order': 50,
    },

    # --- Management Area (3) ---
    {
        'name': 'Ryan Tasseff',
        'role_es': 'Gerente de ReDIB',
        'role_en': 'ReDIB Manager',
        'group': Person.MANAGEMENT,
        'affiliation': 'ReDIB',
        'photo_url': 'https://www.redib.net/upload/secciones-publicas/'
                     'headshot-201702-small_foto.jpeg',
        'order': 0,
    },
    {
        'name': 'Cristina Álvarez de Lara Sánchez',
        'role_es': 'Gestión',
        'role_en': 'Management',
        'group': Person.MANAGEMENT,
        'affiliation': 'BioImaC',
        'photo_url': 'https://www.redib.net/upload/secciones-publicas/'
                     'cals_foto.jpg',
        'order': 10,
    },
    {
        'name': 'Ana Penadés Blasco',
        'role_es': 'Gestión',
        'role_en': 'Management',
        'group': Person.MANAGEMENT,
        'affiliation': 'Imaging La Fe',
        'photo_url': 'https://www.redib.net/upload/secciones-publicas/'
                     'foto-ana-penades-2_foto.jpg',
        'order': 20,
    },
]


USER_AGENT = (
    'Mozilla/5.0 (ReDIB-marketing-site-import; +https://redib.net) '
    'python-urllib/3.12'
)


class Command(BaseCommand):
    help = (
        "Populate the Team / Equipo page with the 14 Person snippets "
        "(ES + EN), downloading their headshot photos into Wagtail's "
        "image library. Idempotent."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        es = Locale.objects.get(language_code='es')
        en = Locale.objects.get(language_code='en')
        image_model = get_image_model()

        # Where headshot files land on disk before being ingested into Wagtail.
        download_dir = Path(settings.MEDIA_ROOT) / 'marketing' / 'team'
        download_dir.mkdir(parents=True, exist_ok=True)

        download_results = []  # (name, photo_attached_bool, note)

        for person_spec in ROSTER:
            name = person_spec['name']
            photo = self._get_or_create_image(
                image_model, download_dir, person_spec['photo_url'], name
            )
            note = 'photo OK' if photo is not None else 'photo MISSING'
            download_results.append((name, photo is not None, note))

            es_person = self._upsert_person(
                locale=es,
                spec=person_spec,
                role=person_spec['role_es'],
                photo=photo,
                translation_key=None,
            )
            self._upsert_person(
                locale=en,
                spec=person_spec,
                role=person_spec['role_en'],
                photo=photo,
                translation_key=es_person.translation_key,
            )

            self.stdout.write(
                f"  {name}  ({person_spec['group']})  — {note}"
            )

        # Summary
        ok = sum(1 for _, attached, _ in download_results if attached)
        missing = len(download_results) - ok
        self.stdout.write(self.style.SUCCESS(
            f"populate_team: {len(ROSTER)} people; "
            f"{ok} with photo, {missing} without."
        ))

    # ------------------------------------------------------------------
    # Image ingest
    # ------------------------------------------------------------------

    def _get_or_create_image(self, image_model, download_dir, url, person_name):
        """Find-or-create a Wagtail Image for this person.

        Idempotency strategy: title is `Team photo: <name>`. If an Image with
        that exact title already exists, reuse it.
        """
        title = f"Team photo: {person_name}"
        existing = image_model.objects.filter(title=title).first()
        if existing is not None:
            return existing

        # Pick filename based on slugified person name + extension from URL.
        parsed = urlparse(url)
        ext = os.path.splitext(parsed.path)[1].lower() or '.jpg'
        if ext not in ('.jpg', '.jpeg', '.png', '.gif', '.webp'):
            ext = '.jpg'
        slug = slugify(person_name) or 'person'
        local_path = download_dir / f"{slug}{ext}"

        # Download if not already cached on disk.
        if not local_path.exists():
            try:
                req = Request(url, headers={'User-Agent': USER_AGENT})
                with urlopen(req, timeout=20) as resp:
                    data = resp.read()
                    # Sanity check: reject obvious HTML error pages.
                    ctype = resp.headers.get('Content-Type', '')
                    if 'image' not in ctype.lower() and len(data) < 1024:
                        self.stderr.write(
                            f"  [WARN] {person_name}: unexpected "
                            f"Content-Type {ctype!r}, skipping."
                        )
                        return None
                local_path.write_bytes(data)
            except (URLError, HTTPError, TimeoutError, OSError) as exc:
                self.stderr.write(
                    f"  [WARN] {person_name}: photo download failed "
                    f"({type(exc).__name__}: {exc}). Continuing without photo."
                )
                return None

        # Create the Wagtail Image record from the downloaded file.
        try:
            with local_path.open('rb') as fh:
                image = image_model.objects.create(
                    title=title,
                    file=File(fh, name=local_path.name),
                )
            return image
        except Exception as exc:  # noqa: BLE001 — log and continue
            self.stderr.write(
                f"  [WARN] {person_name}: Wagtail Image create failed "
                f"({type(exc).__name__}: {exc}). Continuing without photo."
            )
            return None

    # ------------------------------------------------------------------
    # Person snippet upsert
    # ------------------------------------------------------------------

    def _upsert_person(self, *, locale, spec, role, photo, translation_key):
        """Find-or-create a Person snippet for the given locale.

        ES side: pass translation_key=None and we let Django assign a fresh
        one on first create.  EN side: pass the ES side's translation_key
        to link the two translations.
        """
        # Lookup key: (locale, name) is unique enough — names are not
        # duplicated within a single locale across the 14-person roster.
        # On subsequent runs, also accept matching by translation_key on
        # the EN side so we never duplicate.
        existing = None
        if translation_key is not None:
            existing = (
                Person.objects
                .filter(translation_key=translation_key, locale=locale)
                .first()
            )
        if existing is None:
            existing = (
                Person.objects
                .filter(locale=locale, name=spec['name'])
                .first()
            )

        target_fields = {
            'name': spec['name'],
            'role': role,
            'group': spec['group'],
            'affiliation': spec['affiliation'],
            'photo': photo,
            'order': spec['order'],
        }

        if existing is None:
            kwargs = dict(target_fields)
            kwargs['locale'] = locale
            if translation_key is not None:
                kwargs['translation_key'] = translation_key
            person = Person.objects.create(**kwargs)
            return person

        changed = False
        for field, value in target_fields.items():
            if getattr(existing, field) != value:
                # Don't clobber an existing photo with None on re-run if the
                # download has since failed — keep what we had before.
                if field == 'photo' and value is None and existing.photo_id:
                    continue
                setattr(existing, field, value)
                changed = True
        if changed:
            existing.save()
        return existing
