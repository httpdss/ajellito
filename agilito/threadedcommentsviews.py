import threadedcomments.views

from agilito.forms import ThreadedCommentForm
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from threadedcomments.models import ThreadedComment
from django.http import Http404
try:
    from functools import wraps
except ImportError:
    from django.utils.functional import wraps

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
    return threadedcomments.views.comment(*args, **kwargs)

#@restricted
def comment_delete(*args, **kwargs):
    """
    Thin wrapper around threadedviews.comment which checks for project membership
    """
    return threadedcomments.views.comment_delete(*args, **kwargs)
