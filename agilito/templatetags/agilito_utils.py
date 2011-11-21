from django import template
from django.utils.safestring import mark_safe

from django.conf import settings
from agilito import UNRESTRICTED_SIZE, RELEASE

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

@register.filter
def fullusername(u):
    if u.last_name and u.first_name:
        return u'%s %s' % (u.first_name, u.last_name)
    if u.last_name:
        return u.last_name
    if u.first_name:
        return u.first_name
    if u.email:
        return u.email
    return u.username

@register.simple_tag
def agilitorelease():
    return RELEASE
