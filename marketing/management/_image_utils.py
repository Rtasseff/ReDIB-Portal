"""Shared helpers for marketing `populate_*` management commands.

Currently a single function: `get_or_create_image()`. Extracted from
`populate_team.py` (Phase 3b) so subsequent `populate_*` commands can
reuse it (Phase 3c onward).

Idempotency contract: find-or-create a Wagtail `Image` by title. Network
failures and unexpected content types are logged via the caller-provided
`stderr_write` and result in a `None` return — the caller decides what
to do (typically continue without an image rather than abort).
"""
import os
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from django.core.files import File
from django.utils.text import slugify


USER_AGENT = (
    'Mozilla/5.0 (ReDIB-marketing-site-import; +https://redib.net) '
    'python-urllib/3.12'
)


def get_or_create_image(
    image_model,
    download_dir: Path,
    url: str,
    title: str,
    *,
    slug_hint: str = '',
    stderr_write=None,
):
    """Find-or-create a Wagtail Image, downloading the source URL on first call.

    Args:
        image_model: result of `wagtail.images.get_image_model()`.
        download_dir: existing directory on disk for caching downloads.
        url: source URL to fetch on first run.
        title: Wagtail `Image.title`. Used as the idempotency key — re-runs
            with the same title return the existing record.
        slug_hint: optional slug used in the on-disk filename. Falls back
            to slugify(title) if empty.
        stderr_write: optional callable for warning output (typically
            `command.stderr.write`). If None, warnings are silently dropped.

    Returns:
        The wagtailimages.Image instance, or None on failure.
    """
    if stderr_write is None:
        def stderr_write(_msg):
            return None

    existing = image_model.objects.filter(title=title).first()
    if existing is not None:
        return existing

    parsed = urlparse(url)
    ext = os.path.splitext(parsed.path)[1].lower() or '.jpg'
    if ext not in ('.jpg', '.jpeg', '.png', '.gif', '.webp'):
        ext = '.jpg'
    slug = slug_hint or slugify(title) or 'image'
    local_path = download_dir / f"{slug}{ext}"

    if not local_path.exists():
        try:
            req = Request(url, headers={'User-Agent': USER_AGENT})
            with urlopen(req, timeout=20) as resp:
                data = resp.read()
                ctype = resp.headers.get('Content-Type', '')
                if 'image' not in ctype.lower() and len(data) < 1024:
                    stderr_write(
                        f"  [WARN] {title}: unexpected Content-Type "
                        f"{ctype!r}, skipping."
                    )
                    return None
            local_path.write_bytes(data)
        except (URLError, HTTPError, TimeoutError, OSError) as exc:
            stderr_write(
                f"  [WARN] {title}: download failed "
                f"({type(exc).__name__}: {exc}). Continuing without image."
            )
            return None

    try:
        with local_path.open('rb') as fh:
            image = image_model.objects.create(
                title=title,
                file=File(fh, name=local_path.name),
            )
        return image
    except Exception as exc:  # noqa: BLE001 — log and continue
        stderr_write(
            f"  [WARN] {title}: Wagtail Image create failed "
            f"({type(exc).__name__}: {exc}). Continuing without image."
        )
        return None
