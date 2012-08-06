from django.db import models
from django.contrib import messages
from django.utils.translation import ugettext as _
from django.conf import settings


if "notification" in getattr(settings, "INSTALLED_APPS"):
    from notification import models as notification
else:
    notification = None


class TrackingFields(models.Model):

    deleted_on = models.DateTimeField(blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class NotifyMixin(object):

    valid_type = messages.SUCCESS
    valid_message = None
    valid_flash = True

    invalid_type = messages.ERROR
    invalid_message = _("Some validation errors where found on the submitted form.")
    invalid_flash = True

    notify_list = None
    notify_template = None

    def show_invalid_flash(self):
        if self.invalid_flash:
            messages.add_message(self.request, self.invalid_type, self.invalid_message)

    def show_valid_flash(self):
        self.valid_message = _("The %s has been added successfully" % self.object._meta.verbose_name)
        if self.valid_flash:
            messages.add_message(self.request, self.valid_type, self.valid_message)

    def send_notification(self):
        if notification and self.notify_list and self.notify_template:
            notification.send(self.notify_list,
                              self.notify_template,
                              self.get_context_data())
