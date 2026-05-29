from django.contrib import admin

from .models import Newsletter


@admin.register(Newsletter)
class NewsletterAdmin(admin.ModelAdmin):
    list_display = ['title', 'publish_date', 'is_published', 'updated_at']
    list_filter = ['is_published', 'publish_date']
    search_fields = ['title', 'summary', 'slug']
    prepopulated_fields = {'slug': ('title',)}
    ordering = ['-publish_date']
    date_hierarchy = 'publish_date'
