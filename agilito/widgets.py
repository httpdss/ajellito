from itertools import chain

from django import forms
from django.utils.encoding import force_unicode
from django.utils.html import escape, conditional_escape
from django.utils.safestring import mark_safe

class GroupedRadioFieldRenderer(forms.widgets.RadioFieldRenderer):
    def __init__(self, name, value, attrs, choices, offset=0, level=0):
        super(GroupedRadioFieldRenderer, self).__init__(name, value, attrs, choices)
        self.offset = offset
        self.level = level

    def __iter__(self):
        # the tricky part here is keeping track of the index (which is
        # what "offset" is for)
        for value_or_choices, label in self.choices:
            try:
                iter(value_or_choices)
            except TypeError:
                is_iter = False
            else:
                is_iter = True
            if is_iter and not isinstance(value_or_choices, basestring):
                # value_or_choices is choices
                sub = GroupedRadioFieldRenderer(self.name, self.value, self.attrs.copy(), value_or_choices, offset=self.offset, level=self.level+1)
                yield u'<dl class="level%d">\n<dt>%s</dt>\n<dd>%s</dd></dl>' % (self.level, force_unicode(label), sub.render())
                self.offset = sub.offset
            else:
                yield forms.widgets.RadioInput(self.name, self.value, self.attrs.copy(), (value_or_choices, label), self.offset)
                self.offset += 1

class GroupedRadioSelect(forms.RadioSelect):
    renderer = GroupedRadioFieldRenderer
