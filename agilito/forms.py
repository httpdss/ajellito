import types
import datetime
from datetime import date
from dateutil.relativedelta import relativedelta
from operator import attrgetter
from itertools import groupby
from django import forms
from agilito.models import UserStory, Task, TestCase, TaskLog, TestResult,\
    UserProfile, UserStoryAttachment, Impediment

from agilito.widgets import HierarchicRadioSelect, TaskHierarchy
from agilito.fields import GroupedChoiceField

from tagging.forms import TagField
from agilito.widgets import AutoCompleteTagInput, TableSelectMultiple

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

class ImpedimentForm(HiddenHttpRefererForm):
    tasks = forms.MultipleChoiceField(widget=TableSelectMultiple(item_attrs=('id', 'name'), grouper=('user_story', 'name')))

    def __init__(self, *args, **kwargs):
        iteration = kwargs.pop('iteration')

        try:
            impediment = kwargs['instance']
        except KeyError:
            impediment = None

        super(ImpedimentForm, self).__init__(*args, **kwargs)

        #self.fields['tasks'].queryset = Task.objects.filter(user_story__iteration=iteration)
        self.fields['tasks'].choices = [(t.id, t) for t in Task.objects.filter(user_story__iteration=iteration)]

        if impediment is None or impediment.opened is None:
            self.fields['state'] = forms.CharField(widget=forms.HiddenInput, required=False, initial='open')
        elif impediment.resolved is None:
            self.fields['state'] = forms.ChoiceField(choices=[('open', 'Open'), ('resolved', 'Resolved')], initial='open')
        else:
            self.fields['state'] = forms.ChoiceField(choices=[('reopen', 'Reopen')], initial='reopen')

    def clean_state(self):
        state = self.cleaned_data['state']
        if not state in ('open', 'resolved', 'reopen'):
            raise forms.ValidationError('Invalid state selected')
        return state

    def clean(self):
        if 'tasks' not in self.cleaned_data or len(self.cleaned_data['tasks']) == 0:
            raise forms.ValidationError( u'You must select at least one task.')
        return self.cleaned_data

    class Meta:
        model = Impediment
        fields = 'name', 'description', 'state', 'tasks'

class UserStoryForm(HiddenHttpRefererForm):
    def __init__(self,*args, **kwargs):
        try:
            project = kwargs.pop('project')
        except KeyError:
            project = None

        try:
            user_story = kwargs['instance']
            pinned = (not user_story is None and user_story.is_pinned)
        except KeyError:
            user_story = None
            pinned = False

        super(UserStoryForm, self).__init__(*args, **kwargs)

        if project is not None:
            if pinned:
                empty_label = None
                iterations = project.iteration_set.filter(pk=user_story.iteration.id)
            else:
                empty_label = '<Product Backlog>'
                iterations = project.iteration_set.all()

            self.fields['iteration'] = forms.ModelChoiceField(queryset=iterations, required=pinned, empty_label=empty_label)

        self.fields['size'].required = False

    class Meta:
        model = UserStory
        fields = 'name', 'description', 'rank', 'size', 'planned', 'state', 'iteration'

class UserStoryMoveForm(forms.ModelForm):
    copy_tasks = forms.BooleanField(label='Copy tasks', required=False)
    action = forms.ChoiceField(choices=[])

    def __init__(self,*args, **kwargs):
        user_story = kwargs['instance']
        project = kwargs.pop('project')
        it = user_story.iteration

        super(UserStoryMoveForm, self).__init__(*args, **kwargs)

        if user_story.task_set.all().count() == 0:
            self.fields['copy_tasks'].hidden = True

        choices = [('copy_archive', 'Copy and Archive original'), ('copy_fail', 'Copy and Fail original')]
        if user_story.is_blocked or (user_story.state != UserStory.STATES.COMPLETED and it.end_date < datetime.date.today()):
            choices.reverse()
        choices.append(('copy', 'Copy'))

        if not user_story.is_pinned:
            if user_story.iteration is None:
                choices = [('move', 'Move')] + choices
            else:
                choices.append(('move', 'Move'))

        self.fields['action'].choices = choices

        if user_story.iteration is None:
            iterations = project.iteration_set.all()
        else:
            iterations = project.iteration_set.all().exclude(id=user_story.iteration.id)

        self.fields['iteration'] = forms.ModelChoiceField(queryset=iterations, required=False)

    class Meta:
        model = UserStory
        fields = 'iteration', 'action', 'copy_tasks'

class TaskForm(HiddenHttpRefererForm):
    actuals = forms.CharField(widget=forms.HiddenInput, required=False)
    tags = TagField(widget=AutoCompleteTagInput(model=Task), required=False)

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
        fields = 'name', 'tags', 'description', 'state', 'estimate', 'remaining', 'owner', 'actuals'
    
    class Media:
        js = ('/agilito/js/copy_estimate_to_remaining.js',)

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

class TaskField(forms.IntegerField):
    def clean(self, value):
        value = super(TaskField, self).clean(value)
        return Task.objects.get(id=value)

def gen_TaskLogForm(user, cmd=None):
    from django.db import connection
    cur = connection.cursor()

    me = user.id
    today = datetime.date.today()
    recent_task = (today - datetime.timedelta(days = 3)).strftime('%Y-%m-%d')
    last_end = (today - datetime.timedelta(days = 7)).strftime('%Y-%m-%d')
    today = today.strftime('%Y-%m-%d')

    menu = TaskHierarchy(None)
    menu['recent'].name = 'Recent'
    menu['mine'].name = 'My tasks'
    menu['inprogress'].name = 'In progress'
    
    projectmenus = []
    
    projects_sql = """
        select distinct
            p.id,   p.name
        from agilito_project p
        join agilito_project_project_members pm on pm.project_id = p.id and pm.user_id = %(me)d
        join agilito_iteration i on i.project_id = p.id
        where i.start_date <= '%(today)s' and i.end_date >= '%(last_end)s'
        order by p.id
        """ % locals()
    cur.execute(projects_sql)

    projects = cur.fetchall()

    if len(projects) > 5: # this is arbitrary
        mi = menu['all']
        mi.name = 'All'
        projectmenus.append((mi, True))
    else:
        for id, name in projects:
            mi = menu['P%d' % id]
            mi.name = name
            mi.project = id
            projectmenus.append((mi, None))

    # this prevents hitting the database multiple times, quite a bit
    # faster. Plus it automatically sorts the menu
    archived = Task.STATES.ARCHIVED
    tasks_sql = """
        select distinct
            'P',    p.id,   p.name
            ,'IT',  i.id,   i.name
            ,'US',  us.id,  us.name
            ,'TA',  t.id,   t.name

            ,us.rank ,us.state
            ,t.owner_id

            ,max(tlr.id) ,max(tlm.owner_id)
        from agilito_project p
        join agilito_project_project_members pm on pm.project_id = p.id and pm.user_id = %(me)d
        join agilito_iteration i on i.project_id = p.id
        join agilito_userstory us on us.project_id = p.id and us.iteration_id = i.id
        join agilito_task t on t.user_story_id = us.id
        left join agilito_tasklog tlr on tlr.task_id = t.id and tlr.iteration_id = i.id and tlr.date >= '%(recent_task)s'
        left join agilito_tasklog tlm on tlm.task_id = t.id and tlm.iteration_id = i.id and tlm.owner_id = pm.user_id
        where i.start_date <= '%(today)s' and i.end_date >= '%(last_end)s' and t.state != %(archived)d
        group by p.id, p.name, i.id, i.name, us.id, us.name, us.state, us.rank, t.id, t.name, t.owner_id
        order by p.id, i.id, us.rank, us.id, t.id
        """ % locals()

    cur.execute(tasks_sql)
    for row in cur.fetchall():
        ss, to, r, logged = row[-4:]

        for h, add in [(menu['recent'], r), (menu['mine'], to == me or logged), (menu['inprogress'], ss == 20)] + projectmenus:
            if add is None:
                add = (h.project == row[1])

            if not add: continue

            submenu = h.id[0]

            for i in range(0, 12, 3):
                tpe, id, label = row[i:i+3]
                key = '%s%s%d' % (submenu, tpe[0], id)
                elt = h[key]

                elt.name = '%s%d: %s' % (tpe, id, label)
                elt.shrinkable = (tpe == 'P')

                h = elt
            h.task = True

    menu.shrink()

    class TaskLogForm(HiddenHttpRefererForm):
        taskmenu = forms.Field(widget=HierarchicRadioSelect(attrs={'id': 'tasks-select', 'class': 'tasks-select'},
                                                     choices=[],
                                                     hierarchy=menu), required = False)
        task = TaskField(widget=forms.TextInput(attrs={'readonly': 'readonly', 'value': ''}))
        state = forms.ChoiceField(choices=Task.STATES.choices())
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
            fields = 'taskmenu', 'task', 'date', 'time_on_task', 'summary'

    TaskLogForm.base_fields.keyOrder = ['taskmenu',
                                        'task', 
                                        'estimate',
                                        'actuals',
                                        'remaining',
                                        'time_on_task',
                                        'state',
                                        'summary',
                                        'date',
                                        ]

    return TaskLogForm
