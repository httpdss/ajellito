from django.contrib.auth.decorators import login_required
from django.http import Http404
try:
    from functools import wraps
except ImportError:
    from django.utils.functional import wraps

from agilito.models import Project
import html5lib
import ooolib

def restricted(f):
    @wraps(f)
    @login_required
    def wrapper(request, project_id, *args, **kwargs):
        if not request.user.is_superuser:
            try:
                project = request.user.project_set.get(id=project_id)
            except Project.DoesNotExist, msg:
                raise Http404, msg
        return f(request, project_id, *args, **kwargs)
    return wrapper

class HTMLConverter(html5lib.HTMLParser):
    def __init__(self, data):
        html5lib.HTMLParser.__init__(self)
        self.document = self.parse(data)

    def text(self, debug=False):
        return HTMLConverter.__text__(self.document, debug)

    @staticmethod
    def __text__(chunk, debug):
        output = ''

        for child in chunk.childNodes:
            if child.name is None:
                tag = None
            else:
                tag = child.name.lower()

            if tag is None:
                output += child.value
            elif tag in ['font', 'head', 'meta']:
                pass
            elif tag in ['br', 'hr']:
                output += ' \n'
            elif tag in ['p', 'div']:
                output += ' \n' + HTMLConverter.__text__(child, debug) + ' \n'
            elif tag in ['img']:
                output += '[' + child.attributes['src'] + ']'
            elif tag in ['em', 'b', 'strong']:
                output += '*' + HTMLConverter.__text__(child, debug) + '*'
            elif tag in ['tr', 'li']:
                output += HTMLConverter.__text__(child, debug) + ' \n'
            elif tag == 'ul':
                output += ' \n' + HTMLConverter.__text__(child, debug)
            elif tag in ['td', 'a', 'tbody', 'body', 'html', 'span', 'strong']:
                output += HTMLConverter.__text__(child, debug)
            elif tag == 'table':
                output += ' \n' + HTMLConverter.__text__(child, debug) + ' \n'

            ## later we'll just ignore what we don't understand, but
            ## right now I want explicit notification.
            else:
                if debug: print 'Unexpected tag', tag
                output += HTMLConverter.__text__(child, debug)

        return output
