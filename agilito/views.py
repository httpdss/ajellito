import csv, StringIO
import time 
import datetime
import ODTLabels
import types
import settings
from django.core.cache import cache

try:
    settings.CACHE_BACKEND
    CACHE_ENABLED = True
except AttributeError:
    CACHE_ENABLED = False

try:
    import pyExcelerator
    EXCEL_ENABLED = True
except ImportError:
    EXCEL_ENABLED = False

import decimal

from django.core.xheaders import populate_xheaders
from django.utils.translation import ugettext

import cStringIO
import formatter
import htmllib

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot
    MATPLOTLIB_ENABLED = True
except ImportError:
    MATPLOTLIB_ENABLED = False

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
    Impediment, Release
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

        key = 'agilito.views.%s(%s)' % (f.__name__, ','.join([str(vardict[v]) for v in params]))

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

class AgilitoContext(RequestContext):
    """
    This subclass of template.RequestContext automatically populates with
    data needed throughout the application
    """
    def __init__(self, request, dictionary=None, current_project=None, current_story=None):
        self.request = request
        
        if request.user.is_authenticated():
            project_list = request.user.project_set.all()
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

def close_window(request):
    return render_to_response('close_window.html', context_instance=Context())

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
    url = request.GET.get('last_page', reverse('agilito.views.product_backlog', args=[project_id]))

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
    url = request.GET.get('last_page', reverse('agilito.views.product_backlog', args=[project_id]))

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
                archiver = None
                state = None
                if data['action'] == 'copy_archive':
                    state = UserStory.STATES.ARCHIVED
                    archiver = request.user
                elif data['action'] == 'copy_fail':
                    state = UserStory.STATES.FAILED

                story.copy_to_iteration(data['iteration'], data['copy_tasks'], state, archiver)

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

    if len(delobjs) > 0:
        actor = archive
        template = 'archive.html'
    else:
        actor = create_update.delete_object
        template = 'userstory_delete.html'
    return actor(request, object_id=userstory_id,
                                       model=UserStory,
                                       template_name=template,
                                       post_delete_redirect=url,
                                       extra_context={'deleted_objects': delobjs})

@restricted
def backlog(request, project_id, states=None):
    """
    """
    global EXCEL_ENABLED

    project = Project.objects.get(id=project_id)

    if not states:
        states_filter = [s for s in UserStory.STATES.values(include_hidden=True) if not s in UserStory.ENDSTATES]
    else:
        states_filter = [int(s) for s in states.split(':')]

    user_stories = project.backlog(states_filter)

    iterations = Iteration.objects.filter(project__id=project_id, end_date__gte=datetime.date.today())

    newiteration = {}
    if iterations.count() != 0:
        newiteration['starts'] = iterations[iterations.count() - 1].end_date + datetime.timedelta(days=1)
    else:
        newiteration['starts'] = datetime.date.today()

    if newiteration['starts'].weekday() > 4: # weekend
        newiteration['starts'] += datetime.timedelta(days= 7 - newiteration['starts'].weekday())

    sizes = [None] + UserStory.SIZES.values()

    user_stories_count = 0
    size = 0
    for us in user_stories:
        if us.whatami != 'UserStory': continue

        user_stories_count += 1

        if not us.size: continue
        size += us.size

    if EXCEL_ENABLED:
        args = [project_id]
        if states:
            args.append(states)
        full_backlog = reverse('agilito.views.product_backlog', args=args)
    else:
        full_backlog = None

    states_options = []
    for state, name in UserStory.STATES.choices(True):
        states_options.append({ 'state':    state,
                                'name':     name,
                                'selected': state in states_filter,
                                })
    v = project.velocity()

    if not v['sprint_length']:
        newiteration['ends'] = ''
    else:
        newiteration['ends'] = newiteration['starts'] + datetime.timedelta(days=v['sprint_length'] * 7.0 / 5)
        if newiteration['ends'].weekday() > 4: # weekend
            newiteration['ends'] += datetime.timedelta(days= 7 - newiteration['ends'].weekday())

    newiteration['name'] = 'New Iteration created @ %s' % datetime.date.today()

    inner_context = {   'full_backlog'  : full_backlog,
                        'backlog'       : user_stories,
                        'user_stories'  : user_stories_count,
                        'size'          : size,
                        'velocity'      : v, 
                        'accuracy'      : project.size_estimation_accuracy(),
                        'states'        : states_options,
                        'default_backlog': reverse('agilito.views.backlog', args=[project_id]),
                        'sizes'         : sizes,
                        'iterations'    : iterations,
                        'newiteration'  : newiteration
                    }
    context = AgilitoContext(request, { }, current_project=project_id)

    if MATPLOTLIB_ENABLED:
        inner_context['product_backlog_chart'] = reverse('agilito.views.product_backlog_chart', args=[project_id, ""])
    else:
        inner_context['product_backlog_chart'] = None
    return render_to_response('product_backlog.html', inner_context, context_instance=context)

@restricted
def userstory_detail(request, project_id, userstory_id):
    context = AgilitoContext(request, current_project=project_id, current_story=userstory_id)
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
                story.state = UserStory.STATES.DEFINED
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
    context = AgilitoContext(request, current_project=project_id, current_story=userstory_id)
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
    if tasklogs.count() > 0:
        actor = archive
        template = 'archive.html'
    else:
        actor = create_update.delete_object
        template = 'userstory_delete.html'
    return actor(request, object_id=task_id,
                                       model=Task,
                                       template_name=template,
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
    context = AgilitoContext(request, current_project=project_id, current_story=userstory_id)
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
    iterations = Iteration.objects.filter(project__id=project_id,
                                          start_date__lte=date,
                                          end_date__gte=date)
    
    if iterations.count() > 0:
        latest_iteration = iterations.latest('start_date')
    else:
        try:
            latest_iteration = Iteration.objects.filter(project__id=project_id,
                                                        end_date__lte=date).latest('start_date')
        except Iteration.DoesNotExist:
            latest_iteration = None
 
    return latest_iteration

def _iteration_get_burndown_data(it):
    bd = it.burndown_data()
    data = defaultdict(list)

    for row in bd:
        for k, v in row.items():
            if v is not None:
                data[k].append(v)
        if row['remaining'] is not None:
            diff = round(row['ideal'] - row['remaining'], 2)
            data['ideal_tips'].append(diff)
            data['remaining_tips'].append(-diff)
        else:
            data['ideal_tips'].append('-')
            data['remaining_tips'].append('-')
    data['y_max'] = max(data['ideal'] + data['remaining'])
    if len(data['remaining_storypoints']) > 0:
        data['y2_max'] = max(data['remaining_storypoints'])
    else:
        data['y2_max'] = 0

    return data

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
        latest_iteration = _get_iteration(project_id)
    else:
        try:
            latest_iteration = Iteration.objects.get(pk=iteration_id,
                                                     project__pk=project_id)    
        except Iteration.DoesNotExist:
            raise Http404

    if latest_iteration is not None:

        user_stories = latest_iteration.userstory_set.all().order_by('rank')
        planned = sum(i.planned for i in user_stories if i.planned)        
        todo = sum(i.remaining for i in user_stories)
        estimated = sum(i.estimated for i in user_stories)            
        actuals = sum(i.actuals for i in user_stories)
        failures = sum(i.test_failed for i in user_stories)

        total = float(sum(u.size or 1 for u in user_stories)) / 100.0

        open_impediments = Impediment.objects.filter(tasks__user_story__iteration=latest_iteration, resolved=None).order_by('opened').distinct()
        resolved_impediments = Impediment.objects.filter(tasks__user_story__iteration=latest_iteration).exclude(resolved=None).order_by('opened').distinct()

        dn = latest_iteration.day_number(datetime.date.today())
        td = latest_iteration.total_days()

        for i in open_impediments:
            stories = {}
            for t in i.tasks.all():
                if not t.user_story.state in [UserStory.STATES.ACCEPTED, UserStory.STATES.ARCHIVED]:
                    stories[t.user_story.id] = t.user_story.size or 1
            risk = sum(stories.values())
            i.blocked = '%.0f%%' % (float(risk) / total)

        tags = defaultdict(list)
        tasks = Task.objects.filter(user_story__iteration=latest_iteration)
        for task in tasks:
            us = 'us-%d' % task.user_story.id
            ta = 'ta-%d' % task.id
            if task.owner:
                tag = 'owner:' + task.owner.username
                tags[tag].append(ta)
                if not us in tags[tag]:
                    tags[tag].append(us)
            for tag in parse_tag_input(task.tags):
                # tag = tag.name
                if not us in tags[tag]:
                    tags[tag].append(us)
                tags[tag].append(ta)
        tags = [{'tag': tag, 'data': ','.join(tags[tag])} for tag in tags.keys()]

        data = _iteration_get_burndown_data(latest_iteration)

        gc_url = data['google_chart']
        data_url = reverse('agilito.views.iteration_burndown_data',
                           args=[project_id, latest_iteration.id])

        cards_url = reverse('agilito.views.iteration_cards',
                           args=[project_id, latest_iteration.id])

        if EXCEL_ENABLED:
            status_table_url = reverse('agilito.views.iteration_status_table',
                                        args=[project_id, latest_iteration.id])
        else:
            status_table_url = None

        if MATPLOTLIB_ENABLED:
            burndown_chart_url = reverse('agilito.views.iteration_burndown_chart',
                            args=[project_id, latest_iteration.id, 'large'])
            burndown_chart_small_url = reverse('agilito.views.iteration_burndown_chart',
                            args=[project_id, latest_iteration.id, 'small'])
            pbc = reverse('agilito.views.product_backlog_chart', args=[project_id, latest_iteration.id])
        else:
            burndown_chart_url = None
            burndown_chart_small_url = None
            pbc = None

        port = request.META['SERVER_PORT']
        if not port:
            port = '80'
        data_url = quote_plus('http://%s:%s%s' % (request.META['SERVER_NAME'],
                                                  port,
                                                  data_url))
        gc_url = data['google_chart']

        v = latest_iteration.velocity()
        if v is None:
            v = (None, None)
        inner_context = { 'current_iteration' : latest_iteration,
                          'user_stories' : user_stories,
                          'tags': tags,
                          'planned' : planned,
                          'remaining' : todo,
                          'data_url': data_url,
                          'google_chart': gc_url,
                          'estimated' : estimated,
                          'actuals' : actuals,
                          'failures' : failures,
                          'cards_url': cards_url,
                          'status_table_url': status_table_url,
                          'burndown_chart_url': burndown_chart_url,
                          'burndown_chart_small_url': burndown_chart_small_url,
                          'open_impediments': open_impediments,
                          'resolved_impediments': resolved_impediments,
                          'flash': getattr(settings, 'ITERATION_STATUS_FLASH_CHART', True),
                          'product_backlog_chart': pbc,
                          'velocity': v,
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
        rows = latest_iteration.users_total_status
        user_stories = latest_iteration.userstory_set.all().order_by('rank')
        planned = sum(i.planned for i in user_stories if i.planned)         

        inner_context = { 
            'current_iteration' : latest_iteration,
            'rows_bill' : rows,
            'estimated_total': sum(u['estimated'] for u in rows),
            'progress_total': sum(u['progress'] or 0 for u in rows),
            'planned': planned,
        }
    else:
        inner_context = {}

    context = AgilitoContext(request, inner_context, current_project=project_id)
    return render_to_response('iteration_hours.html', context_instance=context)

@restricted
def iteration_burndown_data(request, project_id, iteration_id):
    it = Iteration.objects.get(id=iteration_id, project__id=project_id)

    data = _iteration_get_burndown_data(it)

    ctx = AgilitoContext(request, data, current_project=project_id)
    return render_to_response('burndown_data.csv',
                              context_instance=ctx, 
                              mimetype="text/plain")

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
        size = st.size or 1
        for x, day in enumerate(days):
            # story didn't exist on day we're looking at now; skip
            if st.created > day:
                continue

            # story is completed before the current day; it counts as
            # completed as of now
            if st.state == UserStory.STATES.ACCEPTED and not st.closed is None and st.closed < day:
                completed[x] += size
                continue

            # if the story is archived, consider it existing if it
            # isn't closed (which shouldn't happen!) or if it was
            # closed after the current day
            if st.state == UserStory.STATES.ARCHIVED:
                if not st.closed is None and st.closed > day:
                    existing[x] += size
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

    uso = [None for d in range(len(days))]
    usobase = uso[:]
    usc = uso[:]
    uscbase = uso[:]

    for x in ind:
        uso[x] = added[x] + existing[x]
        usobase[x] = -added[x]

        usc[x] = completed[x]
        uscbase[x] = existing[x]

    matplotlib.pyplot.clf()
    width = 0.35       # the width of the bars: can also be len(x) sequence
    p1 = matplotlib.pyplot.bar(ind, uso,   width, color='#1D91DB', bottom=usobase)
    p2 = matplotlib.pyplot.bar(ind, usc, width, color='y', bottom=uscbase)

    matplotlib.pyplot.ylabel('Stories')
    matplotlib.pyplot.xticks(ind, labels)
    for t in matplotlib.pyplot.gca().get_xticklabels():
        t.set_rotation(45)
        t.set_horizontalalignment('right')
        t.set_fontsize(6)
    matplotlib.pyplot.legend( (p1[0], p2[0]), ('Open', 'Accepted'), 'best' )
    matplotlib.pyplot.grid(color='#999999')

    matplotlib.pyplot.axhline(linewidth=2, color='k', zorder=-1)

    matplotlib.pyplot.plot(completed, 'mo-')

    response = HttpResponse(mimetype='image/png')
    matplotlib.pyplot.savefig(response)
    return response

@restricted
@cached
def iteration_burndown_chart(request, project_id, iteration_id, name):
    it = Iteration.objects.get(id=iteration_id, project__id=project_id)

    data = _iteration_get_burndown_data(it)

    matplotlib.pyplot.clf()
    fig = matplotlib.pyplot.figure()

    small = (name == 'small')

    layers = []
    max_h = max(data['ideal'] + data['remaining'])
    max_s = max(data['remaining_storypoints'])
    layers.append((fig.add_subplot(111), 'ro-', data['ideal'], 'Ideal', max_h))
    layers.append((layers[0][0], 'bo-', data['remaining'], 'Hours', max_h))
    layers.append((layers[0][0].twinx(), 'go-', data['remaining_storypoints'], 'Story points', float(max_s) + 0.1))

    x = [str(x) for x in range(1, len(data['ideal']) + 1)]

    for layer, linestyle, dataset, label, y_max in layers:
        layer.plot(dataset, linestyle)
        layer.set_ylabel(label, color=linestyle[0], fontsize=8)

        layer.set_xticks(range(1, len(x) + 1))
        layer.set_xticklabels(x)
        layer.set_ylim(0, float(y_max))

        # workaround: twinx doesn't sync the axes unless you do this
        layer.set_xlim(layers[0][0].get_xlim())

        if small:
            for l in layer.get_xticklabels():
                l.set_rotation(45)
                l.set_horizontalalignment('right')
                l.set_fontsize(6)
            for l in layer.get_yticklabels():
                l.set_fontsize(6)

    matplotlib.pyplot.grid(color='#999999')

    response = HttpResponse(mimetype='image/png')
    # response['Content-Disposition'] = 'attachment; filename=burndown.png'
    matplotlib.pyplot.grid(color='#999999')

    if small:
        dpi = fig.get_dpi()
        fig.set_size_inches(270.0 / dpi, 200.0 / dpi)

    matplotlib.pyplot.savefig(response)
    return response

@restricted
@cached
def iteration_cards(request, project_id, iteration_id):
    it = Iteration.objects.get(id=iteration_id, project__id=project_id)
    tasks = it.task_cards()
    stories = it.story_cards()

    labels = ODTLabels.ODTLabels(settings.CARD_INFO['ini'])
    labels.setSheetType(settings.CARD_INFO['spec'])
    labels.setTemplate(settings.CARD_INFO['template'])

    response = HttpResponse(mimetype='application/vnd.oasis.opendocument.text')
    response['Content-Disposition'] = 'attachment; filename=cards.odt'
    labels.makeLabels(tasks, stories, response)
    return response

def _excel_column(n):
    """
    Returns excel formated column number for n
    
    Expects an int value greater than 0.
    """

    n-=1
    div = n/26
    if div==0:
        return chr(65+n)
    else:
        return _excel_column(div)+chr(65+n%26)

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
@cached
def product_backlog(request, project_id, states=None):
    statename = {}

    if not states:
        states_filter = [UserStory.STATES.DEFINED, UserStory.STATES.SPECIFIED]
    else:
        states_filter = [int(s) for s in states.split(':')]

    for state, name in UserStory.STATES.choices(include_hidden = True):
        statename[state] = name

    stories = UserStory.objects.reset().filter(project__id=project_id).order_by('rank').order_by('id')
    wb = pyExcelerator.Workbook()
    active = wb.add_sheet('Active Product Backlog')
    full = wb.add_sheet('Product Backlog')

    style = pyExcelerator.XFStyle()
    style.font = pyExcelerator.Font()
    style.font.bold = True

    for ws in [active, full]:
        for c, header in enumerate(['Story', 'Rank', 'Name', 'Description', 'State', 'Iteration', 'Size', 'Suggested size']):
            ws.write(0, c, header, style)

    suggested_size = Project.objects.get(id=project_id).suggest_sizes()

    for us in stories:
        if suggested_size.has_key(us.id):
            us.suggested_size = UserStory.SIZES.label(suggested_size[us.id])
        else:
            us.suggested_size = None

    row = [0, 0]
    for story in stories:
        for ws, write, shn in [(full, True, 1), (active, story.state in states_filter, 0)]:
            if not write:
                continue

            row[shn] += 1
            ws.write(row[shn], 0, story.id)

            if not story.rank is None:
                ws.write(row[shn], 1, story.rank)
    
            ws.write(row[shn], 2, story.name)
    
            if not story.description is None:
                try:
                    desc = unicode(story.description).decode('utf-8')
                except:
                    v_a = story.description.encode('ascii', 'ignore')
                    desc = unicode(v_a).decode('utf-8')
    
                f = cStringIO.StringIO()
                wr = formatter.DumbWriter(f)
                fmt = formatter.AbstractFormatter(wr)
                p = htmllib.HTMLParser(fmt)
                p.feed(desc)
                p.close()
    
                ws.write(row[shn], 3, f.getvalue())
    
            ws.write(row[shn], 4, statename[story.state])
    
            if not story.iteration is None:
                ws.write(row[shn], 5, story.iteration.name)
    
            if story.size:
                ws.write(row[shn], 6, UserStory.SIZES.label(story.size))
    
            if story.suggested_size:
                ws.write(row[shn], 7, story.suggested_size)

    response = HttpResponse(mimetype='application/application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename=backlog.xls'

    wb.save(response)

    return response

@restricted
@cached
def iteration_status_table(request, project_id, iteration_id):
    it = Iteration.objects.get(id=iteration_id, project__id=project_id)

    style = pyExcelerator.XFStyle()
    defaultFont = style.font
    defaultPattern = style.pattern

    fade = pyExcelerator.Font()
    fade.colour_index = 55

    bold = pyExcelerator.Font()
    bold.bold = True

    orange = pyExcelerator.Pattern()
    orange.pattern_fore_colour = 436
    orange.pattern = style.pattern.SOLID_PATTERN

    green = pyExcelerator.Pattern()
    green.pattern_fore_colour = 562
    green.pattern = style.pattern.SOLID_PATTERN

    wb = pyExcelerator.Workbook()
    ws = wb.add_sheet('Burndown')

    days= list(rrule(DAILY, cache=True, dtstart=it.start_date, until=it.end_date, byweekday=(MO,TU,WE,TH,FR)))
    days.append(days[-1] + datetime.timedelta(1))
    sprintlength = len(days)

    style.font = bold
    for c, h in enumerate(['task ID', 'priority', 'story', 'task'] + [str(d.date()) for d in days]):
        ws.write(0, c, h, style)

    today = datetime.date.today()
    days = [d.date() for d in filter(lambda d: d.date()<=today, days)]
    for r, t in enumerate(Task.objects.filter(user_story__iteration=it)):
        us = t.user_story

        if t.estimate is None:
            prev = 0
        else:
            prev = decimal.Decimal(t.estimate)

        for c, day in enumerate(days):

            last = decimal.Decimal(t.remaining_for_date(day))

            if last < prev:
                style.pattern = green
            elif last > prev:
                style.pattern = orange
            else:
                style.pattern = defaultPattern

            if last == 0:
                style.font = fade
            else:
                style.font = defaultFont

            ws.write(r + 1, c + 4, float(last), style)
            prev = last

        ws.write(r + 1, 0, t.id)

        if not us.rank is None:
            ws.write(r + 1, 1, us.rank)

        style.font = defaultFont
        style.pattern = defaultPattern
        if us.state == UserStory.STATES.COMPLETED and us.remaining == 0:
            style.pattern = green
        elif t.state != Task.STATES.COMPLETED and us.remaining == 0:
            style.pattern = orange
        elif t.state == Task.STATES.COMPLETED and us.remaining != 0:
            style.pattern = orange
        ws.write(r + 1, 2, us.name, style)

        style.font = defaultFont
        style.pattern = defaultPattern
        if t.estimate is None:
            style.font = fade
        elif t.state == Task.STATES.COMPLETED and last == 0:
            style.pattern = green
        elif t.state != Task.STATES.COMPLETED and last == 0:
            style.pattern = orange
        elif t.state == Task.STATES.COMPLETED and last != 0:
            style.pattern = orange
        ws.write(r + 1, 3, t.name, style)

    style.font = bold
    style.pattern = defaultPattern

    ws.write(r+2, 3, 'Tasks', style)
    for c in range(len(days)):
        colname = _excel_column(c + 5)
        ws.write(r + 2, c + 4, pyExcelerator.Formula("SUM(%s2:%s%d)" % (colname, colname, r + 2)))

    ws.write(r+3, 3, 'Story points', style)
    for c, d in enumerate(days):
        ws.write(r+3, c+4, it.remaining_storypoints(d))

    ws.write(r+4, 3, 'Ideal', style)
    total = '$%s%d' % (_excel_column(5), r + 3)
    sl = sprintlength - 1
    for c in range(sprintlength):
        f = '(%(total)s/%(sl)d) * (%(sl)d - (COLUMN() - 5))' % locals()
        ws.write(r + 4, c + 4, pyExcelerator.Formula(f))

    response = HttpResponse(mimetype='application/application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename=burndown.xls'

    wb.save(response)

    return response

@restricted
@cached
def iteration_export(request, project_id, iteration_id):
    it = Iteration.objects.get(id=iteration_id, project__id=project_id)

    style = pyExcelerator.XFStyle()
    defaultFont = style.font
    defaultPattern = style.pattern

    bold = pyExcelerator.Font()
    bold.bold = True

    wb = pyExcelerator.Workbook()
    ws = wb.add_sheet('Burndown')

    style.font = bold
    for c, h in enumerate(['ID', 'Name', 'Start', 'End']):
        ws.write(0, c, h, style)

    for c, d in enumerate([it.id, it.name, str(it.start_date), str(it.end_date)]):
        ws.write(1, c, d)

    for c, h in enumerate(['ID', 'Story', 'Task', 'Estimate', 'Owner', 'Tags']):
        ws.write(2, c, h, style)

    for r, t in enumerate(Task.objects.filter(user_story__iteration=it)):
        for c, d in enumerate([t.id, t.user_story.name, t.name, float(t.estimate or 0), t.owner.username, t.tags]):
            ws.write(r+3, c, d)

    response = HttpResponse(mimetype='application/application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename=iteration.xls'

    wb.save(response)

    return response

@restricted
@cached
def hours_export(request, project_id, iteration_id):
    it = Iteration.objects.get(id=iteration_id, project__id=project_id)
    users = []
    user_col = {}

    style = pyExcelerator.XFStyle()
    defaultFont = style.font
    defaultPattern = style.pattern

    bold = pyExcelerator.Font()
    bold.bold = True

    wb = pyExcelerator.Workbook()
    ws = wb.add_sheet('Burndown')

    style.font = bold
    for c, h in enumerate(['ID', 'Name', 'Start', 'End']):
        ws.write(0, c, h, style)

    for c, d in enumerate([it.id, it.name, str(it.start_date), str(it.end_date)]):
        ws.write(1, c, d)

    for c, h in enumerate(['ID', 'Story', 'Task', 'Estimate']): # add users later
        ws.write(2, c, h, style)

    tasks = 0
    for r, t in enumerate(Task.objects.filter(user_story__iteration=it)):
        tasks += 1
        for c, d in enumerate([t.id, t.user_story.name, t.name]):
            ws.write(r+3, c, d)

        u = t.owner.username
        if not u in users:
            users.append(u)
            user_col[u] = len(users) + 3

        ws.write(r+3, user_col[u], float(t.estimate or 0))

    for u in users:
        ws.write(2, user_col[u], u, style)

    c1 = _excel_column(5)
    c2 = _excel_column(4 + len(users))
    for r in range(3, tasks + 3):
        ws.write(r, 3, pyExcelerator.Formula("SUM(%s%d:%s%d)" % (c1, r+1, c2, r+1)))
        
    response = HttpResponse(mimetype='application/application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename=iteration.xls'

    wb.save(response)

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

def archive(request, model, post_delete_redirect, object_id=None,
        slug=None, slug_field='slug', template_name=None,
        template_loader=loader, extra_context=None, login_required=False,
        context_processors=None, template_object_name='object'):
    """
    Generic object-delete function.

    The given template will be used to confirm deletetion if this view is
    fetched using GET; for safty, deletion will only be performed if this
    view is POSTed.

    Templates: ``<app_label>/<model_name>_confirm_delete.html``
    Context:
        object
            the original object being deleted
    """
    if extra_context is None: extra_context = {}
    if login_required and not request.user.is_authenticated():
        return redirect_to_login(request.path)

    obj = create_update.lookup_object(model, object_id, slug, slug_field)

    if request.method == 'POST':
        if request.user.is_authenticated():
            obj.archive(request.user)
            request.user.message_set.create(message=ugettext("The %(verbose_name)s was archived.") % {"verbose_name": model._meta.verbose_name})
        return HttpResponseRedirect(post_delete_redirect)
    else:
        if not template_name:
            template_name = "%s/%s_confirm_delete.html" % (model._meta.app_label, model._meta.object_name.lower())
        t = template_loader.get_template(template_name)
        c = RequestContext(request, {
            template_object_name: obj,
        }, context_processors)
        create_update.apply_extra_context(extra_context, c)
        response = HttpResponse(t.render(c))
        populate_xheaders(request, response, model, getattr(obj, obj._meta.pk.attname))
        return response
