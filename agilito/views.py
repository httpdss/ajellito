import csv, StringIO
import time 
import datetime
import ODTLabels
import types
from django.core.cache import cache
from django.contrib.sites.models import Site
from agilito.opendocument import Calc, HTML

from agilito import CACHE_ENABLED, UNRESTRICTED_SIZE, PRINTABLE_CARDS, CACHE_PREFIX, BACKLOG_ARCHIVE

if BACKLOG_ARCHIVE:
    from dulwich.repo import Repo
    from dulwich import object_store as GitObjectStore

import decimal

from django.core.xheaders import populate_xheaders
from django.utils.translation import ugettext
from django.utils.datastructures import SortedDict

from dateutil.rrule import rrule, WEEKLY, DAILY, MO, TU, WE, TH, FR

from tagging.utils import parse_tag_input

try:
    from collections import defaultdict
except ImportError:
    class defaultdict(dict):
        def __init__(self, default_factory=None, *a, **kw):
            if (default_factory is not None and
                not hasattr(default_factory, '__call__')):
                raise TypeError('first argument must be callable')
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

from urllib import quote_plus

from django.template import RequestContext, Context, loader
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.views.generic.list_detail import object_list, object_detail
from django.views.generic import create_update
from django.utils import simplejson
from django import forms
from django.http import Http404

# Decorator wich checks if you are loged in.
from django.contrib.auth.decorators import login_required

# Helpers to handle GET type of requests.
from urllib import quote, urlencode

from agilito.models import Project, Iteration, UserStory, Task, TestCase,\
    TaskLog, UserProfile, User, TestResult, UserStoryAttachment, \
    Impediment, Release, ArchivedBacklog

from agilito.forms import UserStoryForm, UserStoryShortForm, gen_TaskLogForm,\
    TaskForm, TestCaseAddForm, TestCaseEditForm, testcase_form_factory,\
    TestResultForm, UserStoryAttachmentForm, ImpedimentForm, \
    UserStoryMoveForm, IterationImportForm, ReleaseForm, IterationForm

from agilito.tools import restricted

def cached(f):
    def f_cached(*args, **kwargs):
        global CACHE_ENABLED

        if not CACHE_ENABLED:
            return f(*args, **kwargs)

        params = f.func_code.co_varnames[1:f.func_code.co_argcount]
        vardict = dict(zip(params, ['<default>' for d in params]))
        vardict.update(dict(zip(params, args[1:])))
        vardict.update(kwargs)
        u = args[0].user # request.user

        pv = Project.cache_id(vardict['project_id'])

        key = '%s.agilito.views.%s(%s)' % (CACHE_PREFIX, f.__name__, ','.join([str(vardict[v]) for v in params]))

        v = cache.get(key + '#version')
        if v == pv:
            v = cache.get(key + '#value')
            if not v is None:
                return v

        v = f(*args, **kwargs)
        cache.set(key + '#version', pv, 1000000)
        cache.set(key + '#value', v, 1000000)

        return v

    return f_cached

class UserHasNoProjectException(Exception):
    pass

class SideBar(SortedDict):
    class Sub(list):
        pass

    def __init__(self, request):
        super(SideBar, self).__init__(self)
        self.request = request

    def add(self, section, label, url, redirect=False, popup="", props=None):
        if section.find('#') >= 0:
            sid, section = section.split('#', 2)
        else:
            sid = None

        if not self.has_key(section):
            self[section] = SideBar.Sub()

        if sid:
            self[section].id = sid

        if redirect:
            if isinstance(redirect, basestring):
                url = '%s?last_page=%s' % (url, redirect)
            else:
                url = '%s?last_page=%s' % (url, self.request.path)

        entry = {'url': url, 'label': label, 'properties': props}
        if popup:
            entry['popup'] = popup

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
            if hasattr(self[k], 'id'):
                id = self[k].id
                for i in range(len(nv)):
                    if nv[i]['properties'] is None:
                        nv[i]['properties'] = {}
                    if not nv[i]['properties'].has_key('id'):
                        if i == 0:
                            nv[i]['properties']['id'] = id
                        else:
                            nv[i]['properties']['id'] = ('%s-%d' % (id, i))
            f.extend(nv)

        return f

class AgilitoContext(RequestContext):
    """
    This subclass of template.RequestContext automatically populates with
    data needed throughout the application
    """
    def __init__(self, request, dictionary=None, current_project=None, current_story=None):
        self.request = request
        
        if request.user.is_authenticated():
            project_list = request.user.project_set.all().extra(select={'lower_name': 'lower(name)'}).order_by('lower_name')
            if project_list is None or project_list.count() == 0:
                raise UserHasNoProjectException        
        else:
            raise UserHasNoProjectException        

        if current_project is None:
            current_project = project_list[0]
        else:
            current_project = Project.objects.get(pk=current_project)

        if current_story is not None:
            try:
                current_story = UserStory.objects.get(id=current_story)
            except UserStory.DoesNotExist:
                current_story = None            

        if dictionary is None:
            self.dictionary = { 'project_list' : project_list,
                                'current_project' : current_project,
                                'current_story': current_story,
                                'last_page': request.path,
                                }
        else:
            self.dictionary = dictionary
            self.dictionary['project_list'] = project_list
            self.dictionary['current_project'] = current_project
            self.dictionary['current_story'] = current_story
            self.dictionary['last_page'] = request.path
        RequestContext.__init__(self, self.request, self.dictionary)

    def items(self):
        return self.dictionary.items()
    
    def iteritems(self):
        return self.dictionary.iteritems()

# Views

def touch_cache(request, project_id):
    response = HttpResponse(mimetype='text/plain')
    if CACHE_ENABLED:
        Project.touch_cache(project_id)
        response.write('Touched cache for project %s\n' % project_id)
        response.write('CACHE_PREFIX=%s\n' % CACHE_PREFIX)
    else:
        response.write('Caching is disabled')
    return response

def close_window(request):
    return render_to_response('close_window.html', context_instance=Context())

def datelabels(dates, l):
    label = ['mo', 'tu', 'we', 'th', 'fr', 'sa', 'su']
    return list(enumerate([label[d.weekday()][:l] for d in dates]))

@login_required
def index(request):
    """
    Main index, constructs the url to the iteration one project and redirects 
    to it.
    """
    try:    
        context = AgilitoContext(request)
    except UserHasNoProjectException:
        return render_to_response('errorpage.html',
                                  context_instance=\
                                    Context({'error_message' : 
                                             'You are not assigned into any project.',}))


    url = '/%s/iteration/' % (context['current_project'].id,)
    return HttpResponseRedirect(url)


@restricted
def generic_create(request, project_id, *args, **kwargs):
    """ A quicky view to get things off the ground """
    # Must send a 'AgilitoContext'
    kwargs['extra_context'] = AgilitoContext(request, current_project=project_id)
    return create_update.create_object(request, *args, **kwargs)

@restricted
def generic_update(request, project_id, *args, **kwargs):
    """ A quicky view to get things off the ground """
    # Must send a 'AgilitoContext'
    kwargs['extra_context'] = AgilitoContext(request, current_project=project_id)
    return create_update.update_object(request, *args, **kwargs)


@restricted
def add_attachment(request, project_id, userstory_id, instance=None):
    story = UserStory.objects.filter(id=userstory_id,project__id=project_id).get()
    if request.method == 'POST':
        form = UserStoryAttachmentForm(request.POST,
                                       request.FILES,
                                       instance=instance)
        if form.is_valid():
            attachment = form.save(commit=False)
            attachment.user_story = story
            attachment.save()
            return HttpResponseRedirect(form.cleaned_data['http_referer'])
        else:
            print "form invalid: \n", form
    else:
        url = request.GET.get('last_page', story.get_absolute_url())
        url = '/agilito/redirect.html#' + url
        form = UserStoryAttachmentForm(initial={'http_referer' : url},
                                       instance=instance)
    context = AgilitoContext(request, {'form': form,
                                      'story' : story},
                            current_project=project_id)
    return render_to_response('add_attachment.html', context_instance=context)

#### No point in having this function, just kept it here for the record.
#def edit_attachment(request, project_id, userstory_id, attachment_id):
#    attachment = UserStoryAttachment.objects.get(id=attachment_id,
#                                                 user_story__id=userstory_id,
#                                                 user_story__project__id=project_id)
#    return add_attachment(request, project_id, userstory_id, instance=attachment)

@restricted
def delete_attachment(request, project_id, userstory_id, attachment_id):
    att = UserStoryAttachment.objects.get(id=attachment_id, 
                                          user_story__id=userstory_id, 
                                          user_story__project__id=project_id)

    # set the url to return to after deletion
    url = request.GET.get('last_page', att.get_container_url())
    return create_update.delete_object(request, object_id=attachment_id,
                                       model=UserStoryAttachment,
                                       template_name='userstory_delete.html',
                                       post_delete_redirect=url)

@restricted
def impediment_create(request, project_id, iteration_id, instance=None):
    it = Iteration.objects.get(pk=iteration_id)

    if request.method == 'POST':
        form = ImpedimentForm(request.POST, iteration=it, instance=instance)
        if form.is_valid():
            impediment = form.save(commit=False)

            state = form.cleaned_data['state']
            if impediment.id is None:
                # state must be 'open'
                pass
            elif state in ['open', 'reopen']:
                impediment.resolved = None
            else:
                impediment.resolved = datetime.datetime.now()

            impediment.save()
            form.save_m2m()

            return HttpResponseRedirect(form.cleaned_data['http_referer'])

    else:

        url = '/%s/iteration/%s/' % (it.project.id, it.id)
        url = '/agilito/redirect.html#' + url
        form = ImpedimentForm(iteration=it, initial={'http_referer' : url}, instance=instance)

    context = AgilitoContext(request, {'form': form})
    return render_to_response('impediment_edit.html', context_instance=context)

@restricted
def impediment_edit(request, project_id, iteration_id, impediment_id):
    instance = Impediment.objects.get(id=impediment_id)
    return impediment_create(request, project_id, iteration_id, instance)

@restricted
def release_create(request, project_id, instance=None):
    if request.method == 'POST':
        form = ReleaseForm(request.POST, instance=instance, project=Project.objects.get(id=project_id))
        form.save()
        return HttpResponseRedirect(form.cleaned_data['http_referer'])
    else:
        url = request.GET.get('last_page', '/%s/backlog/' % project_id)
        form = ReleaseForm(initial={'http_referer' : url}, project=Project.objects.get(id=project_id), instance=instance)

    context = AgilitoContext(request, {'form': form}, current_project=project_id)
    return render_to_response('generic_action.html', context_instance=context)

@restricted
def release_edit(request, project_id, release_id):
    instance = Release.objects.get(id=release_id)
    return release_create(request, project_id, instance)

@restricted
def release_delete(request, project_id, release_id):
    release = Release.objects.get(id=release_id, project__id = project_id)

    # set the url to return to after deletion
    url = request.GET.get('last_page', reverse('agilito.views.backlog', args=[project_id]))

    return create_update.delete_object(request, object_id=release_id,
                                       model=Release,
                                       template_name='userstory_delete.html',
                                       post_delete_redirect=url)

@restricted
def iteration_create(request, project_id, instance=None):
    if request.method == 'POST':
        form = IterationForm(request.POST, instance=instance, project=Project.objects.get(id=project_id))
        form.save()
        return HttpResponseRedirect(form.cleaned_data['http_referer'])
    else:
        url = request.GET.get('last_page', '/%s/backlog/' % project_id)
        form = IterationForm(initial={'http_referer' : url}, instance=instance, project=Project.objects.get(id=project_id))

    context = AgilitoContext(request, {'form': form}, current_project=project_id)
    return render_to_response('generic_action.html', context_instance=context)

@restricted
def iteration_edit(request, project_id, iteration_id):
    instance = Iteration.objects.get(id=iteration_id)
    return iteration_create(request, project_id, instance)

@restricted
def iteration_delete(request, project_id, iteration_id):
    iteration = Iteration.objects.get(id=iteration_id, project__id = project_id)

    # set the url to return to after deletion
    url = request.GET.get('last_page', reverse('agilito.views.backlog', args=[project_id]))

    delobjs = list(iteration.userstory_set.all())

    return create_update.delete_object(request, object_id=iteration_id,
                                       model=Iteration,
                                       template_name='userstory_delete.html',
                                       post_delete_redirect=url,
                                       extra_context={"title": "Are you sure you want to delete this iteration? This iteration has these stories attached", 'deleted_objects': delobjs})

@restricted
def userstory_create(request, project_id, iteration_id=None, instance=None):
    if request.method == 'POST':
        form = UserStoryForm(request.POST, instance=instance, project=Project.objects.get(id=project_id))
        if form.is_valid():
            story = form.save(commit=False)
            story.project_id = project_id
            story.save()
            return HttpResponseRedirect(form.cleaned_data['http_referer'])
    else:
        fallback_url = '/%s/backlog/' % project_id
        if not (iteration_id is None):
            fallback_url = Iteration.objects.get(id=iteration_id).get_absolute_url()
        url = request.GET.get('last_page', fallback_url)
        url = '/agilito/redirect.html#' + url
        form = UserStoryForm(initial={'http_referer' : url},
                             instance=instance,
                             project=Project.objects.get(id=project_id))

    context = AgilitoContext(request, {'form': form}, current_project=project_id)
    return render_to_response('userstory_edit.html', context_instance=context)

@restricted
def userstory_move(request, project_id, userstory_id):
    instance = UserStory.objects.get(pk=userstory_id, project__pk=project_id)
    project=Project.objects.get(id=project_id)

    if request.method == 'POST':
        form = UserStoryMoveForm(request.POST, instance=instance, project=project)
        if form.is_valid():
            story = form.save(commit=False)
            data = form.cleaned_data

            if data['action'] == 'move':
                story.iteration = data['iteration']
                story.save()
            else:
                if data['action'] == 'copy_fail':
                    state = UserStory.STATES.FAILED
                else:
                    state = UserStory.STATES.DEFINED

                story.copy_to_iteration(data['iteration'], data['copy_tasks'], state)

            url = request.GET.get('last_page', story.get_absolute_url())
            url = '/agilito/redirect.html#' + url
            return HttpResponseRedirect(url)
    else:
        form = UserStoryMoveForm(instance=instance, project=project)

    context = AgilitoContext(request, {'object': instance, 'action': 'Copy/Move User Story', 'form': form}, current_project=project_id)
    return render_to_response('generic_action.html', context_instance=context)

@restricted
def userstory_edit(request, project_id, userstory_id):
    instance = UserStory.objects.get(pk=userstory_id, project__pk=project_id)
    if instance.iteration is None:
        return userstory_create(request, project_id, instance=instance)
    else:
        return userstory_create(request, project_id,
                                iteration_id=instance.iteration.id,
                                instance=instance)
 
@restricted
def userstory_delete(request, project_id, userstory_id):
    obj = UserStory.objects.get(id=userstory_id, project=project_id)

    # set the url to return to after deletion
    url = request.GET.get('last_page', obj.get_container_url())
    # check if you were on the details view of a us.    
    if url.find('userstory') != -1:
        url = obj.get_container_url()
   
    delobjs = []
    attachments = list(obj.userstoryattachment_set.all())
    if attachments:
        delobjs.append(['Attachments', attachments])
    tasks = []
    for task in obj.task_set.all():
        tasks.append(task)
        tasklogs = list(task.tasklog_set.all())
        if tasklogs: 
            tasks.append(tasklogs)
    if tasks:
        delobjs.extend(['Tasks', tasks])
    testcases = []
    for testcase in obj.testcase_set.all():
        testcases.append(testcase)
        testresults = list(testcase.testresult_set.all())
        if testresults:
            testcases.append(testresults)
    if testcases:
        delobjs.extend(['TestCases', testcases])

    return create_update.delete_object(request, object_id=userstory_id,
                                       model=UserStory,
                                       template_name='userstory_delete.html',
                                       post_delete_redirect=url,
                                       extra_context={'deleted_objects': delobjs})

@restricted
def backlog(request, project_id, states=None, suggest=None):
    """
    """
    if not states:
        states = '%d:%d' % (UserStory.STATES.DEFINED, UserStory.STATES.SPECIFIED)
        return HttpResponseRedirect( reverse('agilito.views.backlog', args=[project_id, states]))

    project = Project.objects.get(id=project_id)

    states_filter = [int(s) for s in states.split(':')]

    if suggest:
        if not UserStory.STATES.ACCEPTED in states_filter:
            states_filter = sorted(states_filter + [UserStory.STATES.ACCEPTED])
        backlog = project.backlog_suggest(states_filter, suggest)
    else:
        backlog = project.backlog(states_filter)

    iterations = Iteration.objects.filter(project__id=project_id, end_date__gte=datetime.date.today())

    newiteration = {}
    if iterations.count() != 0:
        newiteration['starts'] = iterations[iterations.count() - 1].end_date + datetime.timedelta(days=1)
    else:
        newiteration['starts'] = datetime.date.today()

    if newiteration['starts'].weekday() > 4: # weekend
        newiteration['starts'] += datetime.timedelta(days= 7 - newiteration['starts'].weekday())

    if UNRESTRICTED_SIZE:
        sizes = None
    else:
        sizes = [None] + UserStory.SIZES.values()

    states_options = []
    for state, name in UserStory.STATES.choices():
        states_options.append({ 'state':    state,
                                'name':     name,
                                'selected': state in states_filter,
                                })
    velocity = backlog.velocity

    if not velocity.sprint_length:
        newiteration['ends'] = ''
    else:
        newiteration['ends'] = newiteration['starts'] + datetime.timedelta(days=velocity.sprint_length)
        if newiteration['ends'].weekday() > 4: # weekend
            newiteration['ends'] += datetime.timedelta(days= 7 - newiteration['ends'].weekday())

    newiteration['name'] = 'New Iteration created @ %s' % datetime.date.today()

    sidebar = SideBar(request)

    sidebar.add('Actions', 'Add User Story',
        reverse('story_from_backlog', args=[project_id]),
        redirect=True,
        props={'class': "add-object"})

    sidebar.add('Actions', 'Add Iteration',
        reverse('iteration_create', args=[project_id]),
        redirect=True,
        props={'class': "add-object"})

    sidebar.add('Actions', 'Add Release',
        reverse('release_create', args=[project_id]),
        redirect=True,
        props={'class': "add-object"})

    if not UNRESTRICTED_SIZE:
        if suggest is None or suggest == 'estimates':
            sidebar.add('Review', 'Suggest sizes based on actuals',
                reverse('agilito.views.backlog', args=[project_id, str(UserStory.STATES.ACCEPTED), 'actuals']))
        if suggest is None or suggest == 'actuals':
            sidebar.add('Review', 'Suggest sizes based on estimates',
                reverse('agilito.views.backlog', args=[project_id, str(UserStory.STATES.ACCEPTED), 'estimates']))
        if suggest in ('estimates', 'actuals'):
            sidebar.add('Review', 'Remove size suggestions',
                reverse('agilito.views.backlog', args=[project_id]))

    if suggest:
        args=[project_id, states, suggest]
    else:
        args=[project_id, states]
    sidebar.add('Reports', 'Backlog in spreadsheet format', reverse('agilito.views.backlog_ods', args=args))

    sidebar.add('Reports', 'Backlog Evolution',
        reverse('agilito.views.product_backlog_chart',
                args=[project_id, ""]),
        popup="chart")

    sidebar.add('save-changes#Backlog changed', 'Save Changes',
        '#',
        props={'onclick': "savechanges(); return false;"})
    sidebar.add('Backlog changed', 'Cancel Changes',
        '#',
        props={'onclick': "window.location.reload(); return false;"})

    try:
        earliest_archive = ArchivedBacklog.objects.filter(project__id=project_id).order_by('stamp')[0]
    except ArchivedBacklog.DoesNotExist:
        earliest_archive = None
    except IndexError:
        earliest_archive = None

    inner_context = {   'sidebar'       : sidebar.ifenabled(),
                        'backlog'       : backlog.backlog,
                        'user_stories'  : backlog.story_count,
                        'size'          : backlog.size,
                        'velocity'      : velocity,
                        'states'        : states_options,
                        'sizes'         : sizes,
                        'iterations'    : iterations,
                        'newiteration'  : newiteration,
                        'earliest_archive': earliest_archive,
                    }
    if suggest:
        inner_context['suggestions'] = backlog.suggestions
    context = AgilitoContext(request, { }, current_project=project_id)

    return render_to_response('product_backlog.html', inner_context, context_instance=context)

@restricted
def userstory_detail(request, project_id, userstory_id):
    sidebar = SideBar(request)
    sidebar.add('Actions', 'Edit this story',
        reverse('agilito.views.userstory_edit', args=[project_id, userstory_id]),
        redirect=True,
        props={'class': "edit-object"})

    story = UserStory.objects.get(id=userstory_id)
    if story.iteration:
        url = reverse('iteration_status_with_id', args=[project_id, story.iteration.id])
    else:
        url = '/%s/backlog/' % project_id
    sidebar.add('Actions', 'Delete this story',
        reverse('agilito.views.userstory_delete', args=[project_id, userstory_id]),
        redirect=url,
        props={'class': "delete-object"})

    sidebar.add('Actions', 'Add an attachment',
        reverse('agilito.views.add_attachment', args=[project_id, userstory_id]),
        redirect=True,
        props={'class': "add-object"})
    sidebar.add('Actions', 'Add a task',
        reverse('agilito.views.task_create', args=[project_id, userstory_id]),
        redirect=True,
        props={'class': "add-object"})
    sidebar.add('Actions', 'Add a test case',
        reverse('agilito.views.testcase_create', args=[project_id, userstory_id]),
        redirect=True,
        props={'class': "add-object"})

    context = AgilitoContext(request, {'sidebar': sidebar}, current_project=project_id, current_story=userstory_id)
    queryset = UserStory.objects.filter(project__pk=project_id)
    
    try:
        rv =  object_detail(request, queryset=queryset, template_name='userstory_detail.html',
                            object_id=userstory_id, extra_context=context)
        return rv
    except UserStory.DoesNotExist:
        raise Http404
       


#
# testcase_create and task_create are candidates for generalization and
# refactoring, also xxx_details, xxx_delete, etc. Maybe a agilito_object_details?
#
@restricted
def task_create(request, project_id, userstory_id, instance=None):
    story = UserStory.objects.get(id=userstory_id)
    if request.method == 'POST':
        form = TaskForm(request.POST, instance=instance,
                        project=Project.objects.get(pk=project_id))
        if form.is_valid():
            task = form.save(commit=False)
            task.user_story = story

            if task.actuals > 0:    # there are hours logged against this task
                if task.is_defined and task.remaining != 0:
                    task.state = Task.STATES.IN_PROGRESS
                elif task.is_in_progress and task.remaining == 0:
                    task.state = Task.STATES.COMPLETED
                elif task.is_complete:
                    task.remaining = 0
                elif task.remaining == 0:
                    task.state = Task.STATES.COMPLETED
            else:
                if task.is_complete:
                    task.remaining = 0  # maybe you want to set the task complete
                                        # but not log hours.

            task.save(user=request.user)

            # this code has changed compared to what is in the timelog
            story = task.user_story
            total_tasks = story.task_set.all().count()
            if story.task_set.filter(state=Task.STATES.DEFINED).count() == total_tasks:
                story.state = UserStory.STATES.SPECIFIED
            elif story.task_set.filter(state=Task.STATES.COMPLETED).count() == total_tasks:
                story.state = UserStory.STATES.COMPLETED
            else:
                story.state = UserStory.STATES.IN_PROGRESS
            story.save()

            return HttpResponseRedirect(form.cleaned_data['http_referer'])
    else:
        url = request.GET.get('last_page', story.get_absolute_url())
        url = '/agilito/redirect.html#' + url
        initial = {'http_referer' : url,
                   'actuals': getattr(instance, 'actuals', 0)}
        form = TaskForm(initial=initial, instance=instance,
                        project=Project.objects.get(pk=project_id))

    context = AgilitoContext(request, {'form': form,
                                      'story': story},
                            current_project=project_id)
    return render_to_response('task_create.html', context_instance=context)

@restricted
def task_edit(request, project_id, userstory_id, task_id):
    instance = Task.objects.get(id=task_id)
    return task_create(request, project_id, userstory_id, instance)

@restricted
def task_detail(request, project_id, userstory_id, task_id):
    sidebar = SideBar(request)
    sidebar.add('Actions', 'Edit this task',
        reverse('agilito.views.task_edit', args=[project_id, userstory_id, task_id]),
        redirect=True,
        props={'class': "edit-object"})
    sidebar.add('Actions', 'Delete this task',
        reverse('agilito.views.task_delete', args=[project_id, userstory_id, task_id]),
        redirect=reverse('agilito.views.userstory_detail', args=[project_id, userstory_id]),
        props={'class': "delete-object"})

    context = AgilitoContext(request, {'sidebar': sidebar}, current_project=project_id, current_story=userstory_id)
    queryset = Task.objects.filter(user_story__project__pk=project_id, user_story__id=userstory_id)

    return object_detail(request, queryset=queryset, template_name='task_detail.html',
                         template_object_name='task',
                         object_id=task_id, extra_context=context)

@restricted
def task_delete(request, project_id, userstory_id, task_id):
    task = Task.objects.get(id=task_id, user_story__id=userstory_id, user_story__project__id=project_id)

    # set the url to return to after deletion
    url = request.GET.get('last_page', task.get_container_url())
    # check if you were on the details view of a us.    
    if url.find('task') != -1:
        url = task.get_container_url()

    tasklogs = task.tasklog_set.all()
    return create_update.delete_object(request, object_id=task_id,
                                       model=Task,
                                       template_name='userstory_delete.html',
                                       post_delete_redirect=url,
                                       extra_context={'deleted_objects': tasklogs})

@restricted
def testcase_create(request, project_id, userstory_id, instance=None):
    story = UserStory.objects.get(pk=userstory_id)
    if request.method == 'POST':
        form = testcase_form_factory(request.POST, instance, project=story.project)   
        if form.is_valid():
            test_case = form.save(commit=False)
            if isinstance(form, TestCaseAddForm): # only set the user_story if
                                                  # adding, not editing!
                test_case.user_story = story
            test_case.save()
            return HttpResponseRedirect(form.cleaned_data['http_referer'])
    else:
        url = request.GET.get('last_page', story.get_absolute_url())
        url = '/agilito/redirect.html#' + url
        form = testcase_form_factory(instance=instance,
                                     initial={'http_referer' : url},
                                     project=story.project)

    context = AgilitoContext(request, {'form': form,
                                      'story': story },
                            current_project=project_id)
    return render_to_response('testcase_create.html', context_instance=context)

@restricted
def testcase_edit(request, project_id, userstory_id, testcase_id):
    instance = TestCase.objects.get(id=testcase_id)
    return testcase_create(request, project_id, userstory_id, instance)

@restricted
def testcase_detail(request, project_id, userstory_id, testcase_id):
    sidebar = SideBar(request)
    sidebar.add('Actions', 'Edit this testcase',
        reverse('agilito.views.testcase_edit', args=[project_id, userstory_id, testcase_id]),
        redirect=True,
        props={'class': "edit-object"})
    sidebar.add('Actions', 'Delete this testcase',
        reverse('agilito.views.testcase_delete', args=[project_id, userstory_id, task_id]),
        redirect=reverse('userstory_detail', args=[project_id, userstory_id]),
        props={'class': "delete-object"})
    sidebar.add('Actions', 'Add a test result',
        reverse('agilito.views.agilito.views.testresult_create', args=[project_id, userstory_id, testcase_id]),
        redirect=True,
        props={'class': "add-object"})

    context = AgilitoContext(request, {'sidebar': sidebar}, current_project=project_id, current_story=userstory_id)
    queryset = TestCase.objects.filter(user_story__pk=userstory_id, 
                                       user_story__project__pk=project_id)

    return object_detail(request, queryset=queryset, template_name='testcase_detail.html',
                          object_id=testcase_id, extra_context=context)

@restricted
def testcase_delete(request, project_id, userstory_id, testcase_id):
    testcase = TestCase.objects.get(id=testcase_id, user_story__id=userstory_id, user_story__project__id=project_id)

    # set the url to return to after deletion
    url = request.GET.get('last_page', testcase.get_container_url())
    # check if you were on the details view of a us.    
    if url.find('testcase') != -1:
        url = testcase.get_container_url()


    testresults = testcase.testresult_set.all()
    return create_update.delete_object(request, object_id=testcase_id,
                                       model=TestCase,
                                       template_name='testcase_delete.html',
                                       post_delete_redirect=url,
                                       extra_context={'deleted_objects': testresults})

# ToDo: Remove the userstory_id field? Makes sense?
@restricted
def testresult_create(request, project_id, userstory_id, testcase_id, instance=None):
    testcase = TestCase.objects.get(id=testcase_id, user_story__id=userstory_id,
                                    user_story__project__id=project_id)
    if request.method == 'POST':
        form = TestResultForm(request.POST, instance=instance, 
                              project=testcase.user_story.project)
        if form.is_valid():
            testresult = form.save()
            return HttpResponseRedirect(form.cleaned_data['http_referer'])
    else:
        if instance is None:
            # Go with default data
            instance = TestResult(test_case=testcase, tester=request.user,
                                  date=datetime.datetime.today(), result=0)
        url = request.GET.get('last_page', testcase.get_absolute_url())
        url = '/agilito/redirect.html#' + url
        form = TestResultForm(initial={'http_referer' : url},
                              instance=instance,
                              project=testcase.user_story.project)

    context = AgilitoContext(request, {'form': form,
                                      'testcase': testcase },
                            current_project=project_id)    
    return render_to_response('testresult_create.html', context_instance=context)

def testresult_edit(request, project_id, userstory_id, testcase_id, testresult_id):
    testresult = TestResult.objects.get(pk=testresult_id)
    return testresult_create(request, project_id, userstory_id, testcase_id, instance=testresult)

@restricted
def testresult_detail(request, project_id, userstory_id, testcase_id, testresult_id):
    context = AgilitoContext(request, { 'testcase' : TestCase.objects.get(user_story__id=userstory_id,
                                                                         pk=testcase_id,
                                                                         user_story__project__id=project_id),
                                     },
                            current_project=project_id,
                            current_story=userstory_id)
    queryset = TestResult.objects.filter(id=testresult_id, test_case__id=testcase_id,
                                         test_case__user_story__id=userstory_id,
                                         test_case__user_story__project__id=project_id)
    return object_detail(request, queryset=queryset, template_name='testresult_detail.html',
                          object_id=testresult_id, extra_context=context)

@restricted
def testresult_delete(request, project_id, userstory_id, testcase_id, testresult_id):
    testresult = TestResult.objects.get(id=testresult_id,
                                        test_case__id=testcase_id,
                                        test_case__user_story__id=userstory_id, 
                                        test_case__user_story__project__id=project_id)

    # set the url to return to after deletion
    url = request.GET.get('last_page', testresult.get_container_url())
    # check if you were on the details view of a us.    
    if url.find('testresult') != -1:
        url = testresult.get_container_url()

    return create_update.delete_object(request, object_id=testresult_id,
                                       model=TestResult,
                                       template_name='userstory_delete.html',
                                       post_delete_redirect=url)



@restricted
def search(request, project_id):
    """
    Search page
    """    

    AVAILABLE_MODELS = { 'User Story' : UserStory,
                         'Task' :   Task,
                         'Test Case': TestCase,} 

    PREFIX = { 'User Story' : 'US',
               'Task' : 'TA',
               'Test Case': 'TC',
             } 

    query_statement = request.GET.get('query', '')
    model = request.GET.get('model', '')
    pageN = request.GET.get('pagesize', '')

    try:
        paginate_by = int(pageN)
    except ValueError:
        paginate_by = 20
    
    # Not used right now
    querystring = urlencode(dict(query=query_statement))

    queryset = AVAILABLE_MODELS.get(model, UserStory).query(query_statement,
                                                            project_id=project_id)
    prefix = PREFIX.get(model, 'US')

    try:
        context = AgilitoContext(request, {'query': query_statement,
                                          'resultcount': queryset.count,
                                          'querystring': querystring,
                                          'prefix' : prefix,
                                          }, current_project=project_id)
    except UserHasNoProjectException:
        return render_to_response('errorpage.html',
                                  context_instance=Context({'error_message' : 
                                                            'You are not assigned into any project.',}))

    return object_list(request, queryset=queryset.order_by('id'), paginate_by=paginate_by,
                       template_name='search.html',
                       extra_context=context)


def _get_iteration(project_id, date=None):
    # In case there are overlapping iterations we are going to pick
    # the one with the latest start date.    
    if date is None:
        date = datetime.date.today()

    try:
        return Iteration.objects.filter(project__id=project_id, start_date__lte=date, end_date__gte=date).latest('start_date')
    except Iteration.DoesNotExist:
        pass

    try:
        return Iteration.objects.filter(project__id=project_id, end_date__lte=date).latest('start_date')
    except Iteration.DoesNotExist:
        pass
 
    return None

@restricted
def iteration_import(request, project_id):
    project = Project.objects.get(id=project_id)

    highest_rank = UserStory.objects.exclude(rank=None).order_by('-rank')
    if highest_rank.count() == 0:
        rank = 1
    else:
        rank = highest_rank[0].rank + 1

    if request.method == 'POST':
        form = IterationImportForm(project_id, request.POST)
        if form.is_valid():
            iteration, stories = form.cleaned_data['data']

            if not iteration['id']:
                it = Iteration()
                it.project = project
                it.start_date = iteration['start']
                it.end_date = iteration['end']
                it.name = iteration['name']
                it.save()
            else:
                it = Iteration.objects.get(project=project, id=iteration['id'])

            for story in stories:
                if story['id']:
                    st = UserStory.objects.get(project=project, iteration=it, id=story['id'])
                else:
                    st = UserStory()
                    st.project = project
                    st.iteration = it
                    st.rank = rank
                    rank += 1
                st.name = story['name']
                st.save()

                for task, estimate, owner, tags in story['tasks']:
                    t = Task()
                    t.user_story = st
                    t.name = task
                    t.estimate = estimate
                    t.remaining = estimate
                    if owner:
                        t.owner = User.objects.get(username=owner)
                    if len(tags) != 0:
                        t.tags = ', '.join('"%s"' % tg.replace('"', "'") for tg in tags)
                    t.save()

            url = reverse('iteration_status_with_id', args=[project_id, it.id])
            return HttpResponseRedirect(url)
    else:
        form = IterationImportForm(project_id, initial={'data': 'ID\tName\tStart\tEnd\n\nID\tStory\tTask\tEstimate\tOwner\tTags'})

    context = AgilitoContext(request, {'form': form}, current_project=project_id)
    return render_to_response('iteration_import.html', context_instance=context)

@restricted
def iteration_status(request, project_id, iteration_id=None, template='iteration_status.html'):
    if iteration_id is None:
        iteration = _get_iteration(project_id)
    else:
        try:
            iteration = Iteration.objects.get(pk=iteration_id, project__pk=project_id)    
        except Iteration.DoesNotExist:
            raise Http404

    if iteration is not None:
        status = iteration.status()

        tags = defaultdict(list)
        for tag, items in status.tags.items():
            for item in items:
                tags[tag].append('%s-%d' % (item.whatami[:2].lower(), item.id))
        tags = [{'tag': tag, 'data': ','.join(tags[tag])} for tag in tags.keys()]

        sidebar = SideBar(request)
        sidebar.add('Actions', 'Edit this iteration',
            reverse('agilito.views.iteration_edit', args=[project_id, iteration.id]),
            redirect=True,
            props={'class': "edit-object"})

        sidebar.add('Actions', 'Add User Story',
            reverse('story_from_iteration',
                    args=[project_id, iteration.id]),
            redirect=True,
            props={'class': "add-object"})

        sidebar.add('Actions', 'Report Impediment',
            reverse('agilito.views.impediment_create',
                    args=[project_id, iteration.id]),
            redirect=True,
            props={'class': "add-object"})

        sidebar.add('Actions', 'Import Iteration',
            reverse('agilito.views.iteration_import',
                    args=[project_id]),
            redirect=True,
            props={'class': "add-object"})

        sidebar.add('Actions', 'Delete this iteration',
            reverse('agilito.views.iteration_delete', args=[project_id, iteration.id]),
            redirect='/%s/iteration/' % project_id,
            props={'class': "delete-object"})

        sidebar.add('Reports', 'Task Cards',
            reverse('agilito.views.iteration_cards',
                    args=[project_id, iteration.id]))

        sidebar.add('Reports', 'Task Status',
            reverse('agilito.views.iteration_status_table',
                    args=[project_id, iteration.id]))

        sidebar.add('Reports', 'Iteration Export',
            reverse('agilito.views.iteration_export',
                    args=[project_id, iteration.id]))

        try:
            ArchivedBacklog.objects.filter(project__id=project_id, stamp__lte=iteration.start_date).order_by('stamp')[0]
            sidebar.add('Reports', 'Product backlog at iteration start',
                reverse('agilito.views.backlog_archived',
                        args=[project_id, '%04d-%02d-%02d' % (iteration.start_date.year, iteration.start_date.month, iteration.start_date.day)]))
        except IndexError:
            pass

        sidebar.add('Reports', 'Burndown Chart',
            reverse('agilito.views.iteration_burndown_chart',
                    args=[project_id, iteration.id]),
                    props={'target': "_burndown"})

        sidebar.add('Reports', 'Backlog Evolution',
            reverse('agilito.views.product_backlog_chart',
                    args=[project_id, iteration.id]))

        sidebar.add('Reports', 'Task Board',
            reverse('agilito.views.taskboard',
                        args=[project_id, iteration.id]),
            popup="taskboard")

        status.burndown.labels = datelabels(status.burndown.dates, 1)

        inner_context = { 'current_iteration' : iteration,
                          'tags': tags,
                          'sidebar': sidebar.ifenabled(),
                          'stories' : status.stories,
                          'unsized': status.burndown.unsized_stories,
                          'planned' : status.size,
                          'remaining' : status.remaining,
                          'estimated' : status.hours,
                          'actuals' : status.time_spent,
                          'failures' : status.failures,
                          'burndown': status.burndown,
                          'impediments': status.impediments,
                          'velocity': status.velocity,
                          'comment_on': iteration,
                          'us_accepted_percentage': status.stories_accepted_percentage,
                          }
    else:
        inner_context = {}

    context = AgilitoContext(request, inner_context, current_project=project_id)
    return render_to_response(template, context_instance=context)

@restricted
def taskboard(request, project_id, iteration_id=None):
    return iteration_status(request, project_id, iteration_id=iteration_id, template='taskboard.html')

@restricted
def iteration_hours(request, project_id, iteration_id=None):

    if iteration_id is None:
        latest_iteration = _get_iteration(project_id)
    else:
        try:
            latest_iteration = Iteration.objects.get(pk=iteration_id,
                                                     project__pk=project_id)    
        except Iteration.DoesNotExist:
            raise Http404

    if latest_iteration is not None:
        sidebar = SideBar(request)

        sidebar.add('Reports', 'Export Hours', reverse('agilito.views.hours_export', args=[project_id, latest_iteration.id]))

        rows = latest_iteration.users_total_status
        user_stories = latest_iteration.userstory_set.all().order_by('rank')
        planned = sum(i.size for i in user_stories if i.size)         

        inner_context = { 
            'current_iteration' : latest_iteration,
            'rows_bill' : rows,
            'estimated_total': sum(u['estimated'] for u in rows),
            'progress_total': sum(u['progress'] or 0 for u in rows),
            'planned': planned,
            'sidebar': sidebar.ifenabled(),
        }
    else:
        inner_context = {}

    context = AgilitoContext(request, inner_context, current_project=project_id)
    return render_to_response('iteration_hours.html', context_instance=context)

@restricted
def product_backlog_chart(request, project_id, iteration_id):
    today = datetime.date.today()

    if iteration_id:
        it = Iteration.objects.get(id=iteration_id, project__id=project_id)
        start_date = it.start_date
        end_date = it.end_date
        if end_date > today:
            end_date = today

        days= list(rrule(DAILY, cache=True, dtstart=it.start_date, until=end_date, byweekday=(MO,TU,WE,TH,FR)))
        days = [d.date() for d in days]
        days.append(days[-1] + datetime.timedelta(1))
        labels = [str(d) for d in days]

        stories = UserStory.objects.filter(iteration=it).order_by('created')

        leeway = 5
    else:
        stories = UserStory.objects.filter(project__id = project_id).order_by('created')

        us_start = stories[0].created
        it = Iteration.objects.filter(project__id=project_id).order_by('start_date')[0]
        it_start = it.start_date

        if us_start < it_start:
            start_date = us_start
            days = [start_date]
            labels = ['']
        else:
            start_date = it_start
            days = []
            labels = []

        it = Iteration.objects.filter(project__id=project_id, end_date__gte=start_date, start_date__lte=today).order_by('end_date')
        for i in it:
            days.append(i.end_date)
            labels.append(i.name)

        leeway = 1

    existing = [0 for d in range(len(days))]
    added = existing[:]
    completed = existing[:]

    added_after = stories[0].created
    if added_after < start_date:
        added_after = start_date

    for st in stories:
        size = st.size or 0
        for x, day in enumerate(days):
            # story didn't exist on day we're looking at now; skip
            if st.created > day:
                continue

            # story is completed before the current day; it counts as
            # completed as of now
            if st.state == UserStory.STATES.ACCEPTED and not st.closed is None and st.closed < day:
                completed[x] += size
                continue

            # if the story wasn't created on day 0 and the current day
            # isn't day 0, consider it added-after-start
            if st.created > added_after and day >= added_after: # st.created > days[leeway]:
                added[x] += size
                continue

            # if the story doesn't match all these criteria, consider
            # it existing-at-start
            existing[x] += size

    ind = range(len(days))

    us_open = [None for d in ind]
    us_closed = us_open[:]

    for x in ind:
        us_open[x] = added[x] + existing[x]
        us_closed[x] = completed[x]
    # ind, labels
    # completed

    data = {
        'open': us_open,
        'closed': us_closed,
        'completed': completed,
        'xlabels': labels
    }

    context = AgilitoContext(request, data)
    return render_to_response('backlog_evolution.html', context_instance=context)

@restricted
@cached
def iteration_burndown_chart(request, project_id, iteration_id):
    it = Iteration.objects.get(id=iteration_id, project__id=project_id)

    data = it.status().burndown
    data.labels = datelabels(data.dates, 2)
    data.iteration = {'name': it.name, 'starts': it.start_date, 'ends': it.end_date}

    context = AgilitoContext(request, {'burndown': data})
    return render_to_response('burndown_chart.html', context_instance=context)

@restricted
@cached
def iteration_cards(request, project_id, iteration_id):
    it = Iteration.objects.get(id=iteration_id, project__id=project_id)
    status = it.status()

    tasks = []
    stories = []

    for story in status.stories:
        stories.append({
                        'StoryID': story.id,
                        'StoryName': story.name,
                        'StoryDescription': story.description,
                        'StoryRank': story.relative_rank,
                        'StorySize': UserStory.SIZES.label(story.size)
                        })
        for task in story.tasks['all']:
            tasks.append({
                        'TaskID': task.id,
                        'TaskName': task.name,
                        'TaskDescription': task.description,
                        'TaskEstimate': task.estimate,
                        'TaskRemaining': task.remaining,
                        'TaskOwner': task.owner,
                        'TaskTags': ', '.join(task.taglist),
                        'StoryID': story.id,
                        'StoryName': story.name,
                        'StoryDescription': story.description,
                        'StoryRank': story.relative_rank,
                        })

    labels = ODTLabels.ODTLabels(PRINTABLE_CARDS.ini)
    labels.setSheetType(PRINTABLE_CARDS.selected)
    labels.setTemplate(PRINTABLE_CARDS.template)

    response = HttpResponse(mimetype='application/vnd.oasis.opendocument.text')
    response['Content-Disposition'] = 'attachment; filename=cards.odt'
    labels.makeLabels(tasks, stories, response)
    return response

def _ods_column(n):
    """
    Returns excel formated column number for n
    
    Expects an int value greater than 0.
    """

    n-=1
    div = n/26
    if div==0:
        return chr(65+n)
    else:
        return _ods_column(div)+chr(65+n%26)

def backlog_cmd_set_iteration(context, cmd):
    if cmd['id'] != 'new':
        it = Iteration.objects.get(id=int(cmd['id']))
    else:
        it = Iteration()
        it.project = context['project']
        it.name = cmd['name']
        it.start_date = cmd['starts']
        it.end_date = cmd['ends']
        it.save()

    context['iteration'] = it

def backlog_cmd_assign_story(context, cmd):
    story = UserStory.objects.get(id=int(cmd['id']))
    story.iteration = context['iteration']
    story.save()

def backlog_cmd_set_size(context, cmd):
    if cmd['size'] == 'null':
        size = None
    else:
        size = int(cmd['size'])

    story = UserStory.objects.get(id=int(cmd['id']))
    story.size = size
    story.save()

def backlog_cmd_rank(context, cmd):
    def getObject(desc):
        if desc['class'] == 'Release':
            return Release.objects.get(id=int(cmd['id']))
        elif cmd['class'] == 'UserStory':
            return UserStory.objects.get(id=int(cmd['id']))
        else:
            return None

    target = cmd['target']
    after = cmd['after']
    if after['class'] == 'Release':
        after = Release.objects.get(id=int(after['id']))
    elif after['class'] == 'UserStory':
        after = UserStory.objects.get(id=int(after['id']))
    else:
        after = None

    if after is None:
        newrank = 'min'
    elif after.rank is None:
        newrank = 'max'
    else:
        newrank = after.rank + 1

    context['project'].reorder_backlog(target['class'].lower(), int(target['id']), newrank)
    context['compact'] = True

backlog_command_execute = {
        'set-iteration' : backlog_cmd_set_iteration,
        'assign-story'  : backlog_cmd_assign_story,
        'assign-story'  : backlog_cmd_assign_story,
        'set-size'      : backlog_cmd_set_size,
        'rank'          : backlog_cmd_rank,
    }
@restricted
def backlog_save(request, project_id):
    project = Project.objects.get(id=project_id)

    if request.method == 'POST':
        context = {'project': project, 'compact': False}
        for cmd in simplejson.loads(request.POST['command-queue']):
            backlog_command_execute[cmd['command']](context, cmd)
        if context['compact']:
            project.compact_ranks()

    url = request.GET.get('last_page', project.get_absolute_url())
    return HttpResponseRedirect(url)

@restricted
def backlog_archived(request, project_id, date=None):
    if BACKLOG_ARCHIVE is None:
        raise Http404

    if date is None:
        try:
            date = request.POST['archivedate']
        except KeyError:
            raise Http404

    year, month, day = [int(d) for d in date.split('-')]
    date = datetime.datetime(year, month, day, 23, 59, 59)

    try:
        archived = ArchivedBacklog.objects.filter(project__id=project_id, stamp__lte=date).order_by('-stamp')[0]
    except ArchivedBacklog.DoesNotExist:
        raise Http404
    except IndexError:
        raise Http404

    response = HttpResponse(mimetype='application/vnd.oasis.opendocument.spreadsheet')
    response['Content-Disposition'] = 'attachment; filename=backlog.ods'

    repo = Repo(BACKLOG_ARCHIVE)
    response.write(GitObjectStore.tree_lookup_path(repo.object_store.__getitem__, str(archived.commit), '%d.ods' % int(project_id)))
    return response

@restricted
@cached
def backlog_ods(request, project_id, states=None, suggest=None):
    states_filter = [int(s) for s in states.split(':')]

    project = Project.objects.get(id=project_id)
    if suggest:
        backlog = project.backlog_suggest(states_filter, suggest)
    else:
        backlog = project.backlog(states_filter)

    statename = {}
    for state, name in UserStory.STATES.choices(include_hidden = True):
        statename[state] = name

    calc = Calc('Product Backlog')

    header_row = ['Story', 'Rank', 'Name', 'Description', 'State', 'Iteration', 'Size']
    if suggest:
        header_row.append('Suggested size (based on %s)' % suggest)
        if suggest == 'estimates':
            header_row.append('Estimate (hours)')
        else:
            header_row.append('Actuals (hours)')
        header_row.append('Pct')

    for c, header in enumerate(header_row):
        calc.write((0, c), header, {'bold': True})

    row = 0
    for story in backlog.backlog:
        if story.whatami != 'UserStory':
            continue

        row += 1

        calc.write((row, 0), story.id)
        calc.write((row, 1), story.rank)
        calc.write((row, 2), story.name)

        if not story.description is None:
            try:
                desc = unicode(story.description).decode('utf-8')
            except:
                v_a = story.description.encode('ascii', 'ignore')
                desc = unicode(v_a).decode('utf-8')

            calc.write((row, 3), HTML(desc))

        calc.write((row, 4), statename[story.state])
        if story.iteration:
            calc.write((row, 5), story.iteration.name)
        calc.write((row, 6), UserStory.size_label_for(story.size))

        if suggest:
            style = {'bold': False}
            if story.suggestion:
                style['bold'] = story.suggestion.is_benchmark
                calc.write((row, 7), UserStory.size_label_for(story.suggestion.size), style)

                calc.write((row, 8), story.suggestion.hours)

                if story.size:
                    calc.write((row, 9), int(float(story.size * 100) / story.suggestion.size))

    response = HttpResponse(mimetype='application/vnd.oasis.opendocument.spreadsheet')
    response['Content-Disposition'] = 'attachment; filename=backlog.ods'

    calc.save(response)

    return response

@restricted
@cached
def iteration_status_table(request, project_id, iteration_id):
    it = Iteration.objects.get(id=iteration_id, project__id=project_id)
    status = it.status()

    fade = '#C9C9C9'
    orange = '#FF0000'
    green = '#00FF00'

    calc = Calc('Iteration Status')

    days = status.burndown.dates
    sprintlength = status.burndown.days

    for c, h in enumerate(['task ID', 'priority', 'story', 'task'] + [str(d) for d in days]):
        calc.write((0, c), h, {'bold': True})

    row = 1
    for story in status.stories:
        for task in story.tasks['all']:
            row += 1

            calc.write((row, 0), task.id)
            calc.write((row, 1), story.rank)

            style = {'background': False}
            if story.state == UserStory.STATES.COMPLETED and story.remaining == 0:
                style['background'] = green
            elif task.state != Task.STATES.COMPLETED and story.remaining == 0:
                style['background'] = orange
            elif task.state == Task.STATES.COMPLETED and story.remaining != 0:
                style['background'] = orange
            calc.write((row, 2), story.name, style)

            for day, remaining in enumerate(task.remaining_for_day):
                if day == 0:
                    style = {}
                elif task.remaining_for_day[day] < task.remaining_for_day[day - 1]:
                    style = {'background': green}
                elif task.remaining_for_day[day] > task.remaining_for_day[day - 1]:
                    style = {'background': orange}
                else:
                    style = {}

                if not remaining:
                    style['color'] = fade
                    style['bold'] = True

                calc.write((row, day + 4), remaining, style)

            if task.estimate is None:
                style = {'color': fade}
            elif task.state == Task.STATES.COMPLETED and remaining == 0:
                style = {'background': green}
            elif task.state != Task.STATES.COMPLETED and remaining == 0:
                style = {'background': orange}
            elif task.state == Task.STATES.COMPLETED and last != 0:
                style = {'background': orange}
            else:
                style={}
            calc.write((row, 3), task.name, style)

    row += 1
    calc.write((row, 3), 'Tasks', {'bold': True})
    for c in range(len(days)):
        colname = _ods_column(c + 5)
        calc.write((row, c + 4), Formula("=SUM(%s2:%s%d)" % (colname, colname, row)))

    row += 1
    calc.write((row, 3), 'Story points', {'bold': True})
    for c, remaining in enumerate(status.burndown.remaining.points):
        calc.write((row, c+4), remaining)

    row += 1
    calc.write((row, 3), 'Ideal', {'bold': True})
    for c, remaining in enumerate(status.burndown.remaining.ideal):
        calc.write((row, c+4), remaining)

    response = HttpResponse(mimetype='application/vnd.oasis.opendocument.spreadsheet')
    response['Content-Disposition'] = 'attachment; filename=iteration-status.ods'

    calc.save(response)

    return response

@restricted
@cached
def iteration_export(request, project_id, iteration_id):
    it = Iteration.objects.get(id=iteration_id, project__id=project_id)
    status = it.status()

    calc = Calc('Iteration')

    for c, h in enumerate(['ID', 'Name', 'Start', 'End']):
        calc.write((0, c), h, {'bold': True})

    for c, d in enumerate([it.id, it.name, str(it.start_date), str(it.end_date)]):
        calc.write((1, c), d)

    for c, h in enumerate(['ID', 'Story', 'Task', 'Estimate', 'Owner', 'Tags']):
        calc.write((2, c), h, {'bold': True})

    row = 2
    for story in status.stories:
        for task in story.tasks['all']:
            row += 1
            for c, d in enumerate([task.id, task.user_story.name, task.name, task.estimate, task.owner, ', '.join(task.taglist)]):
                calc.write((row, c), d)

    response = HttpResponse(mimetype='application/vnd.oasis.opendocument.spreadsheet')
    response['Content-Disposition'] = 'attachment; filename=iteration.ods'

    calc.save(response)

    return response

@restricted
@cached
def hours_export(request, project_id, iteration_id):
    it = Iteration.objects.get(id=iteration_id, project__id=project_id)

    calc = Calc('Hours')

    for c, h in enumerate(['ID', 'Name', 'Start', 'End']):
        calc.write((0, c), h, {'bold': True})

    for c, d in enumerate([it.id, it.name, str(it.start_date), str(it.end_date)]):
        calc.write((1, c), d)

    for c, h in enumerate(['ID', 'Story', 'Task', 'Estimate']): # add users later
        calc.write((2, c), h, {'bold': True})

    users = []
    users_data = {}
    add_unassigned = False
    for t in Task.objects.filter(user_story__iteration=it):
        if t.owner is None:
            add_unassigned = True
            continue

        if t.owner.id in users:
            continue

        oid = t.owner.id
        users.append(oid)
        users_data[oid] = {}

        if t.owner.first_name and t.owner.last_name:
            users_data[oid]['name'] = '%s %s' % (t.owner.first_name, t.owner.last_name)
        elif t.owner.first_name:
            users_data[oid]['name'] = t.owner.first_name
        elif t.owner.last_name:
            users_data[oid]['name'] = t.owner.last_name
        elif t.owner.email:
            users_data[oid]['name'] = t.owner.email
        else:
            users_data[oid]['name'] = t.owner.username

    users.sort()
    if add_unassigned:
        users.append(None)
        users_data[None] = {}
        users_data[None]['name'] = 'Unassigned'
    for col, user in enumerate(users):
        users_data[user]['col'] = col + 4

    tasks = 0
    for r, t in enumerate(Task.objects.filter(user_story__iteration=it)):
        tasks += 1
        for c, d in enumerate([t.id, t.user_story.name, t.name]):
            calc.write((r+3, c), d)

        if t.owner:
            oid = t.owner.id
        else:
            oid = None

        if t.estimate:
            calc.write((r+3, users_data[oid]['col']), t.estimate)

    for u in users:
        calc.write((2, users_data[u]['col']), users_data[u]['name'], {'bold': True})

    c1 = _ods_column(5)
    c2 = _ods_column(4 + len(users))
    for r in range(3, tasks + 3):
        calc.write((r, 3), Formula("=SUM(%s%d:%s%d)" % (c1, r+1, c2, r+1)))

    response = HttpResponse(mimetype='application/vnd.oasis.opendocument.spreadsheet')
    response['Content-Disposition'] = 'attachment; filename=iteration.ods'

    calc.save(response)

    return response

@restricted
def iteration_burndown(request, project_id, iteration_id):
    it = Iteration.objects.get(id=iteration_id, project__id=project_id)
    ctx = AgilitoContext(request, {'current_iteration': it}, current_project=project_id)
    return render_to_response('iteration_burndown.html',
                              context_instance=ctx)


# XXX fixme: should take a project_id
def _parseTimelogCmd(spec):

    if spec is None:
        return (None, None)

    spec = spec.strip('/')

    if spec == '':
        return (None, None)

    cmd = spec.split('/')


    if len(cmd) != 2:
        return ('Invalid task/project specification "%s"' % spec, None)

    key = cmd[0]
    id = cmd[1]

    if not key in ['task', 'project']:
        return ('Invalid task/project specification "%s"' % spec, None)
    
    try:
        id = int(id)
    except:
        return ('Invalid task/project specification "%s"' % spec, None)

    return (None, (key, id))

@restricted
def timelog(request, project_id, task_id=None, instance=None):
    message = None
    if not task_id is None:
        try:
            task_id = int(task_id)
        except ValueError:
            message = 'Invalid task ID'

    TaskLogForm = gen_TaskLogForm(request.user)

    if message is None and request.method == 'POST':
        form = TaskLogForm(request.POST, instance=instance)
        if form.is_valid():
            tasklog = form.save(commit=False)
            if tasklog.id is None:
                # creating
                tasklog.owner = request.user

            state = int(form.cleaned_data['state'])
            if state == Task.STATES.DEFINED:
                state = Task.STATES.IN_PROGRESS
            if state == Task.STATES.COMPLETED:
                tasklog.task.remaining = 0
            else:
                tasklog.task.remaining = form.cleaned_data['remaining']
            tasklog.task.state = state
            tasklog.task.save(tasklog=tasklog)

            story = tasklog.task.user_story
            if not story.task_set.exclude(state=Task.STATES.COMPLETED).count():
                # all the storie's tasks are Complete
                story.state = UserStory.STATES.COMPLETED
            else:
                story.state = UserStory.STATES.IN_PROGRESS
            story.save()
            message = 'Task %d updated! More?' % form.cleaned_data['task'].id
            form = gen_TaskLogForm(request.user)()
    else:
        form = TaskLogForm(instance=instance)

    if task_id is None:
        selectedTask = 'current_project=project_id'
        project_id = None
    else:
        project_id = Task.objects.get(id=task_id).user_story.project.id
        selectedTask = str(task_id)
    context = AgilitoContext(request, {'form': form,
                                      'message': message,
                                      'selectedTask': selectedTask},
                                    current_project=project_id)
    
    return render_to_response('timelog.html', context_instance=context)

@restricted
def timelog_task(request, project_id, task_id):
    return timelog(request, project_id, task_id)

def dec2str(dec):
    if dec is None:
        return ""
    else:
        return "%.2f" % dec

@login_required
def task_json(request, task_id):
    task = Task.objects.get(id=task_id)
    json = simplejson.dumps(dict(id=task.id,
                                 name=task.name,
                                 story=task.user_story.name,
                                 estimate=dec2str(task.estimate),
                                 remaining=dec2str(task.remaining),
                                 actuals=dec2str(task.actuals),
                                 state=task.state))
    return HttpResponse(json, mimetype='application/json')

def _mk_time(date_string):
    _date = time.mktime(time.strptime(date_string, '%Y-%m-%d'))
    _date = datetime.date.fromtimestamp(_date)
    return _date

def _gen(qset):
    io = StringIO.StringIO()
    writer = csv.writer(io)
    writer.writerow(['Date','Project','Iteration','User Story', 'Task',
                     'User','Time on Task','Summary'])
    yield io.getvalue()
    for item in qset:
        io = StringIO.StringIO()
        writer = csv.writer(io)
        writer.writerow(item.get_csv_row())
        yield io.getvalue()
    return

def _get_date_from_request(request, request_key, kwargs_dict, kwargs_key):
    date_str = request.GET.get(request_key, None)
    if not (date_str is None):
        try:
            kwargs_dict[kwargs_key] = _mk_time(date_str)
        except ValueError:
            pass 

@restricted
def csv_log(request, project_id, username):    
    # create arguments for the query 

    kwargs = dict(owner=User.objects.get(username=username),
                  task__user_story__project__id=project_id)

    # additional arguments
    iteration = request.GET.get('it', None)
    if not (iteration is None):
        kwargs['task__user_story__iteration'] = iteration

    _get_date_from_request(request, 'from_date', kwargs, 'date__gte')
    _get_date_from_request(request, 'to_date', kwargs, 'date__lte')

    tl_set = TaskLog.objects.filter(**kwargs).order_by('date')
    
    response = HttpResponse(_gen(tl_set), mimetype='text/csv')
    response['Content-Disposition'] = 'attachment; filename=tasklogs-for-%s.csv' % username
    
    return response

@restricted
def csv_log_for_project(request, project_id):
    kwargs = dict(task__user_story__project__id=project_id)
    
    # additional arguments
    _get_date_from_request(request, 'from_date', kwargs, 'date__gte')
    _get_date_from_request(request, 'to_date', kwargs, 'date__lte')

    tl_set = TaskLog.objects.filter(**kwargs).order_by('date', 'owner')
    
    response = HttpResponse(_gen(tl_set), mimetype='text/csv')
    response['Content-Disposition'] = 'attachment; filename=tasklogs-for-project.csv'
    
    return response
    
@login_required
def csv_log_all_projects(request):
    kwargs = dict()

    # additional arguments
    _get_date_from_request(request, 'from_date', kwargs, 'date__gte')
    _get_date_from_request(request, 'to_date', kwargs, 'date__lte')

    tl_set = TaskLog.objects.filter(**kwargs).order_by('date', 'owner')
    
    response = HttpResponse(_gen(tl_set), mimetype='text/csv')
    response['Content-Disposition'] = 'attachment; filename=tasklogs-for-all-projects.csv'
    
    return response
