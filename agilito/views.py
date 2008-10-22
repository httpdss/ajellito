import csv, StringIO
import time 
import datetime


try:
    from collections import defaultdict
except ImportError:
    from margerine import defaultdict
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
    TaskLog, UserProfile, User, TestResult, UserStoryAttachment
from agilito.forms import UserStoryForm, UserStoryShortForm, gen_TaskLogForm,\
    TaskForm, TestCaseAddForm, TestCaseEditForm, testcase_form_factory,\
    TestResultForm, UserStoryAttachmentForm

from agilito.tools import restricted

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
        form = UserStoryForm(initial={'http_referer' : url},
                             instance=instance,
                             project=Project.objects.get(id=project_id))

    context = AgilitoContext(request, {'form': form},
                            current_project=project_id)
    return render_to_response('userstory_edit.html', context_instance=context)

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
def backlog(request, project_id):
    """
    """
    user_stories = UserStory.backlogged(project=project_id)
    planned = sum(i.planned for i in user_stories if i.planned)

    context = AgilitoContext(request, { 'user_stories' : user_stories, 'planned':planned }, 
                            current_project=project_id)
        

    return render_to_response('backlog_noajax.html', context_instance=context)




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
                    task.state = 20
                elif task.is_in_progress and task.remaining == 0:
                    task.state = 30
                elif task.is_complete:
                    task.remaining = 0
                elif task.remaining == 0:
                    task.state = 30
            else:
                if task.is_complete:
                    task.remaining = 0  # maybe you want to set the task complete
                                        # but not log hours.
            task.save()

            # this code has changed compatered to what is in the timelog
            story = task.user_story
            total_tasks = story.task_set.all().count()
            if story.task_set.filter(state=10).count() == total_tasks:
                story.state = 10
            elif story.task_set.filter(state=30).count() == total_tasks:
                story.state = 30
            else:
                story.state = 20
            story.save()

            return HttpResponseRedirect(form.cleaned_data['http_referer'])
    else:
        url = request.GET.get('last_page', story.get_absolute_url())
        initial = {'http_referer' : url,
                   'actuals': getattr(instance, 'actuals', 0)}
        form = TaskForm(initial=initial, instance=instance,
                        project=Project.objects.get(pk=project_id))

    context = AgilitoContext(request, {'form': form,
                                      'story': story},
                            current_project=project_id)
    return render_to_response('task_create.html', context_instance=context)

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

    tasklogs = list(task.tasklog_set.all())
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
        form = testcase_form_factory(instance=instance,
                                     initial={'http_referer' : url},
                                     project=story.project)

    context = AgilitoContext(request, {'form': form,
                                      'story': story },
                            current_project=project_id)
    return render_to_response('testcase_create.html', context_instance=context)

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

@restricted
# ToDo: Remove the userstory_id field? Makes sense?
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


@restricted
def iteration_status(request, project_id, iteration_id=None):
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

        data_url = reverse('agilito.views.iteration_burndown_data',
                           args=[project_id, latest_iteration.id])
        data_url = quote_plus('http://%s:%s%s' % (request.META['SERVER_NAME'],
                                                  request.META['SERVER_PORT'],
                                                  data_url))

        inner_context = { 'current_iteration' : latest_iteration,
                          'user_stories' : user_stories,
                          'planned' : planned,
                          'remaining' : todo,
                          'data_url': data_url,
                          'estimated' : estimated,
                          'actuals' : actuals,
                          'failures' : failures, }
    else:
        inner_context = {}

    context = AgilitoContext(request, inner_context, current_project=project_id)
    return render_to_response('iteration_status.html', context_instance=context)

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
    ctx = AgilitoContext(request, data, current_project=project_id)
    return render_to_response('burndown_data.csv',
                              context_instance=ctx, 
                              mimetype="text/plain")

@restricted
def iteration_burndown(request, project_id, iteration_id):
    it = Iteration.objects.get(id=iteration_id, project__id=project_id)
    ctx = AgilitoContext(request, {'current_iteration': it}, current_project=project_id)
    return render_to_response('iteration_burndown.html',
                              context_instance=ctx)


# XXX fixme: should take a project_id
@login_required
def timelog(request, instance=None):

    TaskLogForm = gen_TaskLogForm(request.user)
    message = None

    if request.method == 'POST':
        form = TaskLogForm(request.POST, instance=instance)
        if form.is_valid():
            tasklog = form.save(commit=False)
            if tasklog.id is None:
                # creating
                tasklog.owner = request.user
                tasklog.iteration = tasklog.task.user_story.iteration
                tasklog.old_remaining = tasklog.task.remaining
            state = int(form.cleaned_data['state'])
            if state == 10: # aka 'Defined'
                state = 20  # in progress
            if state == 30: # complete
                tasklog.task.remaining = 0
            else:
                tasklog.task.remaining = form.cleaned_data['remaining']
            tasklog.task.state = state
            tasklog.task.save()
            tasklog.save()
            story = tasklog.task.user_story
            if not story.task_set.exclude(state=30).count():
                # all the storie's tasks are Complete
                story.state = 30
            else:
                story.state = 20
            story.save()
            message = 'Great! More?'
            form = gen_TaskLogForm(request.user)()
    else:
        form = TaskLogForm(instance=instance)

    context = AgilitoContext(request, {'form': form,
                                      'message': message,})
    
    return render_to_response('timelog.html', context_instance=context)

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

