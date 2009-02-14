from itertools import chain

from django import forms
from django.utils.encoding import force_unicode
from django.utils.html import escape, conditional_escape
from django.utils.safestring import mark_safe

from tagging.models import Tag

from django.utils import simplejson

import types

class TaskHierarchy:
    def __init__(self, id):
        self.id = id
        self.name = None
        self.task = False
        self.children = []
        self.shrinkable = False
        self.project = None

    def keys(self):
        return [c.id for c in self.children]
        
    def __getitem__(self, id):
        child = ([c for c in filter(lambda x: x.id == id, self.children)] + [None])[0]
        if child is None:
            child = TaskHierarchy(id)
            self.children.append(child)
        return child

    def shrink(self):
        for child in self.children:
            child.shrink()

        if len(self.children) == 1 and self.children[0].shrinkable:
            self.children = self.children[0].children

    def __print(self, level = 0):
        indent = ' ' * level
        name = self.name
        if name is None: name = ''
        children = ''
        for c in self.children:
            children += c.__print(level + 1)
        return indent + name + '\n' + children

    def __str__(self):
        return self.__print()

class NestedListRadioFieldRenderer(forms.widgets.RadioFieldRenderer):
    def __init__(self, name, value, attrs, choices, hierarchy):
        if attrs.has_key('id'):
            self.id = ' id="%s"' % conditional_escape(force_unicode(attrs['id']))
            del attrs['id']
        else:
            self.id = ''

        super(NestedListRadioFieldRenderer, self).__init__(name, value, attrs, choices)
        self.hierarchy = hierarchy
        self.__rendered = u''
        # self.__index = 0

    def __render(self, data, id = None):
        if type(data) == types.ListType:
            self.__rendered += u'<ul'
            if id:
                self.__rendered += id

            css = []
            if id:
                css.append(self.name + '-root')
                if self.attrs.has_key('class'): css.append(self.attrs['class'])
                self.__rendered += ' class="%s"' % " ".join(css)

            self.__rendered += u'>'
            for entry in data:
                self.__render(entry)
            self.__rendered += u'</ul>\n'
            return

        label = force_unicode(conditional_escape(data.name[:40]).replace(' ', '&nbsp;'))

        self.__rendered += '<li>'

        if data.task:
            self.__rendered += '<span id="%s-%s">' % (self.name, data.id)
            # self.__rendered += force_unicode(forms.widgets.RadioInput(self.name, self.value, self.attrs.copy(), (data, label), self.__index))
            self.__rendered += label
            self.__rendered += '</span>'
            # self.__index += 1

        else:
            self.__rendered += u'<span>' + label + u'</span>\n'
            self.__render(data.children)

        self.__rendered += '</li>\n'

    def render(self):
        # self.__index = 0
        self.__rendered = u''
        self.__render(self.hierarchy.children, self.id)
        return mark_safe(self.__rendered)

class TreeTableRadioFieldRenderer(forms.widgets.RadioFieldRenderer):
    def __init__(self, name, value, attrs, choices, hierarchy):
        self.properties = {}

        for key in ['id']:
            if attrs.has_key(key):
                self.properties[key] = attrs[key]
                del attrs[key]
            else:
                self.properties[key] = ''

        if self.properties['id']:
            self.properties['id'] = ' id="%s"' % conditional_escape(force_unicode(self.properties['id']))

        super(TreeTableRadioFieldRenderer, self).__init__(name, value, attrs, choices)
        self.hierarchy = hierarchy
        self.__rendered = u''
        self.__index = 0
        self.__node = 0

    def __render(self, data, parent):
        if type(data) == types.ListType:
            for entry in data:
                self.__render(entry, parent)
            return

        data, label, opened = data

        id = '%s-%d' % (self.name, self.__node)
        self.__node += 1

        if parent:
            parent = ' class="child-of-%s"' % parent
        else:
            parent = ''


        if isinstance(data, types.StringTypes):
            self.__rendered += '<tr id="%s"%s><td>' % (id, parent)
            self.__rendered += force_unicode(forms.widgets.RadioInput(
                self.name, self.value, self.attrs.copy(), (data, label), self.__index))
            self.__rendered += '</td></tr>\n'
            self.__index += 1

        else:
            self.__rendered += u'<tr id="%s"%s><td>' % (id, parent)
            self.__rendered += conditional_escape(force_unicode(label))
            self.__rendered += u'</td></tr>\n'
            self.__render(data, id)

    def render(self):
        self.__index = 0
        self.__rendered = u'<table%s' % self.properties['id']

        css = []
        if self.attrs.has_key('class'): css.append(self.attrs['class'])
        if len(css) > 0:
            self.__rendered += ' class="%s"' % " ".join(css)
        self.__rendered += '>'

        self.__render(self.hierarchy, None)

        self.__rendered += u'</table>'

        return mark_safe(self.__rendered)

class HierarchicRadioSelect(forms.RadioSelect):
    renderer = NestedListRadioFieldRenderer
    #renderer = TreeTableRadioFieldRenderer

    def __init__(self, *args, **kwargs):
        # Override the default renderer if we were passed one.
        renderer = kwargs.pop('renderer', None)
        self.hierarchy = kwargs.pop('hierarchy', None)
        super(HierarchicRadioSelect, self).__init__(*args, **kwargs)

    def render(self, name, value, attrs=None, choices=()):
        if value is None: value = ''
        str_value = force_unicode(value) # Normalize to string.
        final_attrs = self.build_attrs(attrs)
        return self.renderer(name, str_value, final_attrs, self.choices, self.hierarchy).render()

class AutoCompleteTagInput(forms.TextInput):
    def __init__(self, *args, **kwargs):
        self.__ac_model__ = kwargs['model']
        del kwargs['model']

        super(AutoCompleteTagInput, self).__init__(*args, **kwargs)

    class Media:
        css = {
            'all': ('/agilito/jquery-autocomplete/jquery.autocomplete.css',)
        }
        js = (
            '/agilito/jquery-autocomplete/lib/jquery.bgiframe.min.js',
            '/agilito/jquery-autocomplete/lib/jquery.ajaxQueue.js',
            '/agilito/jquery-autocomplete/jquery.autocomplete.js'
        )

    def render(self, name, value, attrs=None):
        output = super(AutoCompleteTagInput, self).render(name, value, attrs)
        page_tags = Tag.objects.usage_for_model(self.__ac_model__)
        tag_list = simplejson.dumps([tag.name for tag in page_tags], ensure_ascii=False)
        return output + mark_safe(u'''<script type="text/javascript">
            jQuery("#id_%s").autocomplete(%s, {
                width: 150,
                max: 10,
                highlight: false,
                multiple: true,
                multipleSeparator: ", ",
                scroll: true,
                scrollHeight: 300,
                matchContains: true,
                autoFill: true,
            });
            </script>''' % (name, tag_list))
