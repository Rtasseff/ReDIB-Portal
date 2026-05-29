"""
Models for the newsletters app.

Hosts ReDIB HTML newsletters as standalone pages within the portal so they
share the portal's chrome until the public marketing site is migrated here.
"""
from django.db import models
from django.urls import reverse


class Newsletter(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(
        max_length=200,
        unique=True,
        help_text='URL slug, e.g. "spring-2026". Used in /newsletters/<slug>/.'
    )
    publish_date = models.DateField(help_text='Date displayed on the listing.')
    summary = models.TextField(
        help_text='One- or two-line teaser shown on the newsletter index.'
    )
    html_file = models.FileField(
        upload_to='newsletters/',
        help_text='Self-contained HTML file (inline CSS, no external assets).'
    )
    is_published = models.BooleanField(
        default=False,
        help_text='Unpublished newsletters are hidden from the public list.'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-publish_date', '-created_at']

    def __str__(self):
        return f"{self.publish_date:%Y-%m-%d} — {self.title}"

    def get_absolute_url(self):
        return reverse('newsletters:detail', kwargs={'slug': self.slug})
