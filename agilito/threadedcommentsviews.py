import threadedcomments.views

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from threadedcomments.models import ThreadedComment
from django.http import Http404
from django.contrib import messages
from django.conf import settings
from django.utils.translation import ugettext as _
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User
import logging

logger = logging.getLogger('agilito.threadedcommentsview')
try:
    from functools import wraps
except ImportError:
    from django.utils.functional import wraps


if "notification" in getattr(settings, "INSTALLED_APPS"):
    from notification import models as notification
else:
    notification = None


def restricted(f):
    @wraps(f)
    @login_required
    def wrapper(request, *args, **kwargs):
        try:
            ct = get_object_or_404(ContentType, id=int(kwargs['content_type']))
            obj = ct.get_object_for_this_type(id=int(kwargs['object_id']))
        except KeyError:
            try:
                obj = get_object_or_404(ThreadedComment, id=int(kwargs['edit_id'])).content_object
            except KeyError:
                obj = get_object_or_404(ThreadedComment, id=int(kwargs['object_id'])).content_object
        except Exception, msg:
            raise Http404, str(msg)

        if not request.user.is_superuser:
            try:
                project = request.user.project_set.get(id=obj.project.id)
            except Exception, e:
                raise Http404, str(e)
        return f(request, *args, **kwargs)
    return wrapper


#@restricted
def comment(*args, **kwargs):
    """
    Thin wrapper around threadedviews.comment which checks for project membership
    """
    http_response = threadedcomments.views.comment(*args, **kwargs)
    messages.add_message(args[0], messages.SUCCESS, _("Comment added succesfully"))
    if notification:
        sendto_ids = args[0].POST.getlist('sendto')
        if sendto_ids:
            ct = get_object_or_404(ContentType, id=int(kwargs['content_type']))
            obj = ct.get_object_for_this_type(id=int(kwargs['object_id']))
            ids = [int(user_id) for user_id in sendto_ids]
            notify_list = User.objects.filter(pk__in=ids)

            notification.send(notify_list,
                             "agilito_comment_create",
                             {'creator': args[0].user,
                              'comment': args[0].POST.get('comment'),
                              'object_url': obj.get_absolute_url(),
                              'object': obj})
    return http_response


#@restricted
def comment_delete(*args, **kwargs):
    """
    Thin wrapper around threadedviews.comment which checks for project membership
    """

    for a in args:
        logger.error(a)

    for key in kwargs:
        logger.error("%s %s" % (key, kwargs[key]))
    return threadedcomments.views.comment_delete(*args, **kwargs)
