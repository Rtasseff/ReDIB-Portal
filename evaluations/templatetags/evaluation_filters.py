"""
Custom template filters for evaluations app
"""
from django import template

register = template.Library()


@register.filter
def key(dictionary, key_name):
    """
    Access dictionary value by key in templates.
    Usage: {{ my_dict|key:variable }}
    """
    try:
        return dictionary[key_name]
    except (KeyError, TypeError):
        return ''
