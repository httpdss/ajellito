from datetime import date
from dateutil.relativedelta import relativedelta
from operator import attrgetter
from itertools import groupby
from django import forms
from agilito.models import UserStory, Task, TestCase, TaskLog, TestResult,\
    UserProfile, UserStoryAttachment

from agilito.widgets import GroupedRadioSelect
from agilito.fields import GroupedChoiceField

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        exclude = ('user',)

class HiddenHttpRefererForm(forms.ModelForm):
    http_referer = forms.CharField(widget=forms.HiddenInput, required=False)

class UserStoryAttachmentForm(HiddenHttpRefererForm):

#### No point in having this code here, this basicly modifies the queryset for
#### for the user_story field, but since we are not going to modified I commented it.
#    def __init__(self, *args, **kwargs):
#        try:
#            project = kwargs.pop('project')
#        except KeyError:
#            project = None
#
#        super(UserStoryAttachmentForm, self).__init__(*args, **kwargs)

#        if project is not None:
#            us_qset = UserStory.objects.filter(project=project)
#            self.fields['user_story'] = forms.ModelChoiceField(queryset=us_qset,
#                                                               required=False)

    class Meta:
        model = UserStoryAttachment
        exclude = ('user_story',)

class UserStoryForm(HiddenHttpRefererForm):

    def __init__(self,*args, **kwargs):
        try:
            project = kwargs.pop('project')
        except KeyError:
            project = None

        super(UserStoryForm, self).__init__(*args, **kwargs)
        
        if project is not None:
            iterations = project.iteration_set.all()
            self.fields['iteration'] = forms.ModelChoiceField(queryset=iterations,
                                                              required=False)

    class Meta:
        model = UserStory
        fields = 'name', 'description', 'rank', 'planned', 'state', 'blocked', 'iteration'

class TaskForm(HiddenHttpRefererForm):
    actuals = forms.CharField(widget=forms.HiddenInput, required=False)
    def __init__(self,*args, **kwargs):
        try:
            project = kwargs.pop('project')
        except KeyError:
            project = None

        super(TaskForm, self).__init__(*args, **kwargs)
        
        if project is not None:
            owner_qset = project.project_members.all()
            self.fields['owner'] = forms.ModelChoiceField(queryset=owner_qset,
                                                          required=False)

    class Meta:
        model = Task
        fields = 'name', 'description', 'state', 'estimate', 'remaining', 'owner'
    
    class Media:
        js = ('/resources/js/copy_estimate_to_remaining.js',)

class TestCaseAddForm(HiddenHttpRefererForm):

    class Meta:
        model = TestCase
        exclude = ('user_story',)

class TestCaseEditForm(HiddenHttpRefererForm):
    def __init__(self, *w, **kw):
        try:
            project = kw.pop('project')
        except KeyError:
            project = None        

        super(TestCaseEditForm, self).__init__(*w, **kw)

        if project is not None:
            us_qset = UserStory.objects.filter(project=project)
            self.fields['user_story'] = forms.ModelChoiceField(queryset=us_qset)

    class Meta:
        model = TestCase

def testcase_form_factory(data=None, instance=None, initial=None, project=None):
    if initial is None:
        if instance is None and data is None:
            return TestCaseAddForm()
        elif instance is None and not (data is None):
            return TestCaseAddForm(data)
        elif not (instance is None) and data is None:
            return TestCaseEditForm(instance=instance, project=project)
        elif not (instance is None) and not (data is None):
            return TestCaseEditForm(data, instance=instance, project=project)
    else:
        if instance is None and data is None:
            return TestCaseAddForm(initial=initial)
        elif instance is None and not (data is None):
            return TestCaseAddForm(data, initial=initial)
        elif not (instance is None) and data is None:
            return TestCaseEditForm(initial=initial, instance=instance, project=project)
        elif not (instance is None) and not (data is None):
            return TestCaseEditForm(data, initial=initial, instance=instance, project=project)
        

class TestResultForm(HiddenHttpRefererForm):
    def __init__(self, *w, **kw):
        try:
            project = kw.pop('project')
        except KeyError:
            project = None        

        super(TestResultForm, self).__init__(*w, **kw)

        if not self.fields['result'].widget.choices:
            self.fields['result'].widget.choices.pop(0)

        if project is not None:
            tc_qset = TestCase.objects.filter(user_story__project=project)
            tester_qset = project.project_members.all()
            self.fields['test_case'] = forms.ModelChoiceField(queryset=tc_qset)
            self.fields['tester'] = forms.ModelChoiceField(queryset=tester_qset)

    class Meta:
        model = TestResult

class UserStoryShortForm(HiddenHttpRefererForm):
    class Meta:
        model = UserStory
        fields = 'name', 'description'

class TaskField(GroupedChoiceField):
    def clean(self, value):
        value = super(TaskField, self).clean(value)
        return Task.objects.get(id=value[1:])

def gen_TaskLogForm(user):
    max_age = date.today() - relativedelta(months=1)
    qs = Task.objects.filter(tasklog__owner=user,
                             tasklog__task__state__lt=30,
                             tasklog__date__gt=max_age).order_by('-tasklog__date')

    # distinct isn't working well with order_by onto related tables
    recent = []
    for i in qs:
        if i not in recent:
            recent.append(i)
        if len(recent) >= 5:
            break

    #recent.sort(key=attrgetter('user_story_id'))
    recent.sort(key=(lambda x : (x.user_story.project.id, x.user_story.id)))

    grouped_recent = []

    for project, tasks_by_project in groupby(recent, lambda x: x.user_story.project):
        by_project = []
        grouped_recent.append((by_project, project))
        for story, tasks_by_story in groupby(tasks_by_project, attrgetter('user_story')):
            by_project.append((list(('r%d' % task.id, unicode(task)) for task in tasks_by_story), unicode(story)))
    if len(grouped_recent) == 1:
        # throw away the project header
        grouped_recent = grouped_recent[0][0]

    all = Task.objects.filter(user_story__project__project_members=user)\
          .order_by('user_story__project',
                    'user_story__iteration',
                    'user_story__id')

    grouped_all = []
    for project, tasks_by_project in groupby(all, lambda x: x.user_story.project):
        by_project = []
        grouped_all.append((by_project, project))
        for iteration, tasks_by_iteration in groupby(tasks_by_project, lambda x: x.user_story.iteration):
            by_iteration = []
            by_project.append((by_iteration, unicode(iteration or u'Backlog')))
            for story, tasks_by_story in groupby(tasks_by_iteration, attrgetter('user_story')):
                by_iteration.append((list(('a%d' % task.id, unicode(task)) for task in tasks_by_story), unicode(story)))
    if len(grouped_all) == 1:
        # throw away the project header
        grouped_all = grouped_all[0][0]

    if grouped_recent:
        grouped_all = [(grouped_recent, "Recent"), (grouped_all, "All")]

    class TaskLogForm(HiddenHttpRefererForm):
        task = TaskField(widget=GroupedRadioSelect(attrs={'class': 'tasks-select'}),
                         choices=grouped_all)
        state = forms.ChoiceField(choices=Task.STATES)
        estimate = forms.DecimalField(widget=forms.TextInput(attrs={'type': "readonly",
                                                                    'readonly': "readonly",
                                                                    'style' : "border: 0"}),
                                      min_value=0, decimal_places=2, max_digits=5,
                                      required=False)
        remaining = forms.DecimalField(min_value=0, decimal_places=2, max_digits=5)
        actuals = forms.DecimalField(widget=forms.TextInput(attrs={'type': "readonly",
                                                                    'readonly': "readonly",
                                                                    'style' : "border: 0"}),
                                     min_value=0, decimal_places=2, max_digits=5,
                                     required=False)
        date = forms.DateField(initial=str(date.today()))
        class Meta:
            model = TaskLog
            fields = 'task', 'date', 'time_on_task', 'summary'

    TaskLogForm.base_fields.keyOrder = ['task', 
                                        'estimate',
                                        'actuals',
                                        'remaining',
                                        'time_on_task',
                                        'state',
                                        'summary',
                                        'date',
                                        ]

    return TaskLogForm
