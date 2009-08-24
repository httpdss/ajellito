from django import template
from django.utils.safestring import mark_safe

from agilito.models import UserStory

register = template.Library()

@register.filter
def storysize(s):
    if s is None: return '-'
    if s == UserStory.SIZES.INFINITY: return mark_safe('&infin;')
    return UserStory.SIZES.label(s)
