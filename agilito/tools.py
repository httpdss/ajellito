from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.utils.datastructures import SortedDict
try:
    from functools import wraps
except ImportError:
    from django.utils.functional import wraps

from agilito.models import Project
import html5lib

def touch_cache(request, project_id):
    response = HttpResponse(mimetype="text/plain")
    if CACHE_ENABLED:
        Project.touch_cache(project_id)
        response.write("Touched cache for project %s\n" % project_id)
        response.write("CACHE_PREFIX=%s\n" % CACHE_PREFIX)
    else:
        response.write("Caching is disabled")
    return response
    
def cached_view(f):
    def f_cached(*args, **kwargs):
        global CACHE_ENABLED

        if not CACHE_ENABLED:
            return f(*args, **kwargs)

        params = f.func_code.co_varnames[1:f.func_code.co_argcount]
        vardict = dict(zip(params, ['<default>' for d in params]))
        vardict.update(dict(zip(params, args[1:])))
        vardict.update(kwargs)
        u = args[0].user # request.user

        pv = Project.cache_id(vardict["project_id"])

        key = "%s.agilito.views.%s(%s)" % (CACHE_PREFIX, f.__name__, ",".join([str(vardict[v]) for v in params]))

        v = cache.get(key + "#version")
        if v == pv:
            v = cache.get(key + "#value")
            if not v is None:
                return v

        v = f(*args, **kwargs)
        cache.set(key + '#version', pv, 1000000)
        cache.set(key + '#value', v, 1000000)

        return v

    return f_cached



def datelabels(dates, l):
    label = ["mo", "tu", "we", "th", "fr", "sa", "su"]
    return list(enumerate([label[d.weekday()][:l] for d in dates]))

class SideBar(SortedDict):
    class Sub(list):
        pass

    def __init__(self, request):
        super(SideBar, self).__init__(self)
        self.request = request

    def add(self, section, label, url, redirect=False, popup="", props=None):
        if section.find("#") >= 0:
            sid, section = section.split('#', 2)
        else:
            sid = None

        if not self.has_key(section):
            self[section] = SideBar.Sub()

        if sid:
            self[section].id = sid

        if redirect:
            if isinstance(redirect, basestring):
                url = "%s?last_page=%s" % (url, redirect)
            else:
                url = "%s?last_page=%s" % (url, self.request.path)

        entry = {"url": url, "label": label, "properties": props}
        if popup:
            entry["popup"] = popup

        self[section].append(entry)

    def enabled(self):
        return (len(self) > 0)

    def ifenabled(self):
        if self.enabled():
            return self
        return None

    def flattened(self):
        f = []

        for k, v in self.items():
            nv = v[:]
            if hasattr(self[k], "id"):
                id = self[k].id
                for i in range(len(nv)):
                    if nv[i]["properties"] is None:
                        nv[i]["properties"] = {}
                    if not nv[i]["properties"].has_key("id"):
                        if i == 0:
                            nv[i]["properties"]["id"] = id
                        else:
                            nv[i]["properties"]["id"] = ("%s-%d" % (id, i))
            f.extend(nv)

        return f
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

class defaultdict(dict):
    def __init__(self, default_factory=None, *a, **kw):
        if (default_factory is not None and
            not hasattr(default_factory, "__call__")):
            raise TypeError("first argument must be callable")
        dict.__init__(self, *a, **kw)
        self.default_factory = default_factory
    def __getitem__(self, key):
        try:
            return dict.__getitem__(self, key)
        except KeyError:
            return self.__missing__(key)
    def __missing__(self, key):
        if self.default_factory is None:
            raise KeyError(key)
        self[key] = value = self.default_factory()
        return value
    def __reduce__(self):
        if self.default_factory is None:
            args = tuple()
        else:
            args = self.default_factory,
        return type(self), args, None, None, self.iteritems()
    def copy(self):
        return self.__copy__()
    def __copy__(self):
        return type(self)(self.default_factory, self)
    def __deepcopy__(self, memo):
        import copy
        return type(self)(self.default_factory,
                            copy.deepcopy(self.items()))
    def __repr__(self):
        return 'defaultdict(%s, %s)' % (self.default_factory,
                                        dict.__repr__(self))
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
