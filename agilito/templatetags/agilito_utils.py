from django import template
from django.utils.safestring import mark_safe

import settings
from agilito import UNRESTRICTED_SIZE

from agilito.models import UserStory, Task

register = template.Library()

@register.filter
def storysize(s):
    if not UNRESTRICTED_SIZE and s == UserStory.SIZES.INFINITY:
        return mark_safe('&infin;')

    return UserStory.size_label_for(s)

@register.filter
def storystate(s):
    return UserStory.STATES.label(s)

@register.filter
def taskstate(s):
    return Task.STATES.label(s)
