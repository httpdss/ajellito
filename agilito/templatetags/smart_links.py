from django import template
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe
from django.core.urlresolvers import reverse

register = template.Library()

def link_to_profile(matchobj):
    prefix = matchobj.group(1)
    username = matchobj.group(2)
    url_to = reverse("idios.views.profile", args=[username])
    return '%s<a href="%s">@%s</a>' % (prefix, url_to, username)

@register.filter
@stringfilter
def smartlinks(value, autoescape=None):
	from django.utils.html import urlize
	import re
	# Link URLs
	value = urlize(value, nofollow=False, autoescape=autoescape)
    
	# Link hash tags
	value = re.sub(r'(\s+|\A)@([a-zA-Z0-9\-_]*)\b', link_to_profile, value)

	# value = re.sub(r'(\s+|\A)%P(\d+)US(\d+)\b', '%s<a href="%s">%P%sUS%s</a>' % (r'\1', reverse("agilito.views.userstory_detail", args=[r'\2', r'\3']), r'\2', r'\3'), value)
	return mark_safe(value)

smartlinks.is_safe=True
smartlinks.needs_autoescape = True

