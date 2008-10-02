from django.contrib.auth.decorators import login_required
from django.http import Http404
try:
    from functools import wraps
except ImportError:
    from django.utils.functional import wraps

from agilito.models import Project

def restricted(f):
    @wraps(f)
    @login_required
    def wrapper(request, project_id, *args, **kwargs):
        try:
            project = request.user.project_set.get(id=project_id)
        except Project.DoesNotExist, msg:
            raise Http404, msg
        return f(request, project_id, *args, **kwargs)
    return wrapper
