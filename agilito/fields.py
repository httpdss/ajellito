from django import forms
from django.utils.encoding import smart_unicode

class GroupedChoiceField(forms.ChoiceField):
    def clean(self, value):
        """
        Validates that the input is in self.choices.
        """
        if self.required and value in forms.fields.EMPTY_VALUES:
            raise forms.ValidationError(self.error_messages['required'])
        if value in forms.fields.EMPTY_VALUES:
            value = u''
        value = smart_unicode(value)
        if value == u'':
            return value
        valid_values = []
        choices = list(self.choices)
        while choices:
            value_or_choices, label = choices.pop(0)
            try:
                iter(value_or_choices)
            except TypeError:
                is_iter = False
            else:
                is_iter = True
            if is_iter and not isinstance(value_or_choices, basestring):
                # value_or_choices is choices
                choices[:0] = list(value_or_choices)
            else:
                valid_values.append(smart_unicode(value_or_choices))
        if value not in valid_values:
            raise forms.ValidationError(self.error_messages['invalid_choice'] % {'value': value})
        return value
