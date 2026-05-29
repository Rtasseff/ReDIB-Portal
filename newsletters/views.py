"""
Public views for the newsletters app.
"""
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.clickjacking import xframe_options_sameorigin

from .models import Newsletter


def newsletter_list(request):
    """Public list of published newsletters."""
    newsletters = Newsletter.objects.filter(is_published=True)
    return render(request, 'newsletters/list.html', {'newsletters': newsletters})


def newsletter_detail(request, slug):
    """Portal-chrome wrapper page that embeds the newsletter HTML in an iframe."""
    newsletter = get_object_or_404(Newsletter, slug=slug, is_published=True)
    return render(request, 'newsletters/detail.html', {'newsletter': newsletter})


@xframe_options_sameorigin
def newsletter_raw(request, slug):
    """
    Serve the uploaded HTML file as the iframe source.

    Routing through Django (rather than linking directly at MEDIA_URL) lets us
    set X-Frame-Options: SAMEORIGIN so the iframe is allowed in both dev (Django
    serves media) and prod (Caddy serves media but the iframe URL is this view).
    """
    newsletter = get_object_or_404(Newsletter, slug=slug, is_published=True)
    try:
        with newsletter.html_file.open('rb') as f:
            content = f.read()
    except FileNotFoundError:
        raise Http404("Newsletter HTML file is missing on disk.")
    return HttpResponse(content, content_type='text/html; charset=utf-8')
