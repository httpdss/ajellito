import types
import re
import datetime
from datetime import date
from dateutil.relativedelta import relativedelta
from operator import attrgetter
from itertools import groupby
from django import forms
from django.conf import settings
from django.contrib.auth.models import User
from django.utils.translation import ugettext as _
from agilito.models import UserStory, Task, TestCase, TaskLog, TestResult,\
    UserProfile, UserStoryAttachment, Impediment, Iteration, Release, Project,ProjectMember

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

class IterationForm(HiddenHttpRefererForm):
    def __init__(self, *args, **kwargs):
        self.project = kwargs.pop('project')
        super(IterationForm, self).__init__(*args, **kwargs)
        self.fields['start_date'].widget.attrs['class'] = 'show-datepicker'
        self.fields['end_date'].widget.attrs['class'] = 'show-datepicker'

    class Meta:
        model = Iteration

class ReleaseForm(HiddenHttpRefererForm):
    def __init__(self, *args, **kwargs):
        self.project = kwargs.pop('project')
        super(ReleaseForm, self).__init__(*args, **kwargs)
        self.fields['deadline'].widget.attrs['class'] = 'show-datepicker'

    class Meta:
        model = Release

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

class IterationImportForm(forms.Form):
    data = forms.CharField(widget=forms.widgets.Textarea(attrs={'class': 'mceNoEditor'}))
    new_iteration = forms.BooleanField(label=_("Create new iteration"), required=False)
    new_stories = forms.BooleanField(label=_('Create new stories'), required=False)

    def __init__(self, project_id, *args, **kwargs):
        super(IterationImportForm, self).__init__(*args, **kwargs)
        self.project_id = project_id

    def clean_data(self):
        sheet = self.cleaned_data['data']
        rows = []
        rownum = []
        for rn, row in enumerate(sheet.split('\n')):
            r = row.replace('\r', '').split('\t')
            if not len(filter(lambda x: x != '' and not x is None, r)) == 0:
                rows.append(r)
                rownum.append(rn + 1)

        # headers cannot have empty slots
        rows[0] = filter(lambda x: x, rows[0])
        iterationheader = rows[0]
        # validate iteration header
        for i, s in enumerate(['id', 'name', 'start', 'end']):
            if rows[0][i].lower() != s:
                raise forms.ValidationError(_('unexpected header "%{h1}", expected "%{h2}"' ).format(h1=rows[0][i], h2=s))

        for i, cell in enumerate(rows[1]):
            if cell and i >= len(rows[0]):
                raise forms.ValidationError(_('Unexpected "%s" in iteration data' ) % cell)

        if not rows[1][0] and not rows[1][1]:
            raise forms.ValidationError(_('You must specify at least an iteration id or name'))

        if not rows[1][0] and not rows[1][2] and not rows[1][3]:
            raise forms.ValidationError(_('You are creating a new iteration, please specify start and end date'))

        if rows[1][0]:
            try:
                id = int(rows[1][0])
            except ValueError:
                raise forms.ValidationError(_('unexpected iteration ID "%s" (must be numeric)' ).format(rows[1][0]))

            try:
                iteration = Iteration.objects.get(project__id=self.project_id, id=id)
            except Iteration.DoesNotExist:
                raise forms.ValidationError(_('Iteration %d does not exist' ) % id)
        else:
            try:
                iteration = Iteration.objects.get(project__id=self.project_id, name=rows[1][1])
                raise forms.ValidationError(_('An iteration with the same name exists'))
            except:
                pass

        for cell in rows[1][2:4]:
            if cell:
                if not re.match('[0-9]{4}-[0-9]{1,2}-[0-9]{1,2}$', cell):
                    raise forms.ValidationError(_('unexpected date "%s"' ) % cell)

        # iteration is OK
        iteration = {}
        for i, s in enumerate(iterationheader):
            iteration[s.lower()] = rows[1][i]

        # headers cannot have empty slots
        rows[2] = filter(lambda x: x, rows[2])
        sprintheader = rows[2]
        # validate sprint header
        for i, s in enumerate(['id', 'story', 'task', 'estimate', 'owner', 'tags']):
            try:
                if rows[2][i].lower() != s:
                    raise forms.ValidationError(_('unexpected header "%{h1}", expected "%{h2}"' ).format(h1=rows[2][i], h2=s))
            except IndexError:
                if i <= 3:
                    raise forms.ValidationError(_('missing header, expected "%s"' ) % s)

        stories = {}
        story_order = []
        for rn, rowdata in enumerate(rows[3:]):
            rn = 'row %d: ' % rownum[rn + 3]

            for i, cell in enumerate(rowdata):
                if cell and i >= len(rows[2]):
                    raise forms.ValidationError(rn + _('unexpected "%s" in sprint data' ) % cell)

            row = {}
            for i, s in enumerate(sprintheader):
                row[s.lower()] = rowdata[i]

            if not row['id'] and not row['story']:
                raise forms.ValidationError(rn + _( 'you must specify at least a story id or name') )

            if not row['task']:
                raise forms.ValidationError(rn + _( 'you must specify a task name') )

            if row['id']:
                try:
                    id = int(row['id'])
                except ValueError:
                    raise forms.ValidationError(rn + _('unexpected story ID "%s" (must be numeric)' ) % row['id'])

                try:
                    story = UserStory.objects.get(id=id)
                except UserStory.DoesNotExist:
                    raise forms.ValidationError(rn + _('story %d does not exist' ) % id)
                key = id

            else:
                key = row['story']
                id = None

            if not stories.has_key(key):
                story_order.append(key)
                stories[key] = {'id': id, 'name': row['story'], 'tasks': []}

            if stories[key]['name'] and row['story'] and stories[key]['name'] != row['story']:
                raise forms.ValidationError(rn + _('conflicting names for same story' ) % id)
            
            if not row['estimate']:
                raise forms.ValidationError(rn + _( 'you must specify a task estimate') )
            try:
                est = float(row['estimate'])
            except ValueError:
                raise forms.ValidationError(rn + _('unexpected task estimate "%s" (must be numeric)' ) % row['estimate'])

            if row.has_key('owner') and row['owner']:
                username = (row['owner'].split('/')[0]).strip()
                try:
                    owner = User.objects.get(username=username)
                except User.DoesNotExist:
                    raise forms.ValidationError(rn + _('user %s does not exist' ) % username)
                row['owner'] = username
            else:
                row['owner'] = None

            if row.has_key('tags') and row['tags']:
                row['tags'] = [t.strip() for t in row['tags'].split('/')]
            else:
                row['tags'] = []

            stories[key]['tasks'].append((row['task'], row['estimate'], row['owner'], row['tags']))

        return (iteration, [stories[key] for key in story_order])

    def clean(self):
        try:
            for field in self.fields.keys():
                self.cleaned_data[field]
        except KeyError:
            return self.cleaned_data

        it, stories = self.cleaned_data['data']
        ni = self.cleaned_data['new_iteration']
        ns = self.cleaned_data['new_stories']

        if not ni and not it['id']:
            raise forms.ValidationError(_('You are creating a new iteration. Please check the appropriate checkbox to confirm.') )

        if not ns:
            for st in stories:
                if not st['id']:
                    raise forms.ValidationError(_('You are creating a new story. Please check the appropriate checkbox to confirm.') )

        return self.cleaned_data

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
            raise forms.ValidationError(_('Invalid state selected') )
        return state

    def clean(self):
        if 'tasks' not in self.cleaned_data or len(self.cleaned_data['tasks']) == 0:
            raise forms.ValidationError(_('You must select at least one task.') )
        return self.cleaned_data

    class Meta:
        model = Impediment
        fields = 'name', 'description', 'tasks'

class UserStoryForm(HiddenHttpRefererForm):
    tags = TagField(required=False)

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
        fields = 'name', 'description', 'rank', 'size', 'state', 'iteration', 'tags'

class UserStoryMoveForm(forms.ModelForm):
    copy_tasks = forms.BooleanField(label=_('Copy tasks') , required=False)
    action = forms.ChoiceField(choices=[])

    def __init__(self,*args, **kwargs):
        user_story = kwargs['instance']
        project = kwargs.pop('project')
        it = user_story.iteration

        super(UserStoryMoveForm, self).__init__(*args, **kwargs)

        if user_story.task_set.all().count() == 0:
            self.fields['copy_tasks'].hidden = True

        choices = [('copy_fail',_( 'Copy and Fail original') )]
        if user_story.is_blocked or (user_story.state != UserStory.STATES.COMPLETED and (it is None or it.end_date < datetime.date.today())):
            choices.reverse()
        choices.append(('copy',_( 'Copy') ))

        if not user_story.is_pinned:
            if user_story.iteration is None:
                choices = [('move',_( 'Move') )] + choices
            else:
                choices.append(('move',_( 'Move') ))

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
    tags = TagField(required=False)

    def __init__(self,*args, **kwargs):
        try:
            project = kwargs.pop('project')
        except KeyError:
            project = None

        super(TaskForm, self).__init__(*args, **kwargs)
        
        if project is not None:
            pm_values = ProjectMember.objects.filter(project__pk=1).values('user')
            owner_qset = User.objects.filter(pk__in=pm_values)
            
            self.fields['owner'] = forms.ModelChoiceField(queryset=owner_qset,
                                                          required=False)

    class Meta:
        model = Task
        fields = 'name', 'tags', 'description', 'state', 'estimate', 'remaining', 'owner', 'actuals'
    
    class Media:
        js = (settings.STATIC_URL + 'agilito/js/copy_estimate_to_remaining.js',)

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
            pm_values = ProjectMember.objects.filter(project__pk=1).values('user')
            tester_qset = User.objects.filter(pk__in=pm_values)

            self.fields['test_case'] = forms.ModelChoiceField(queryset=tc_qset)
            self.fields['tester'] = forms.ModelChoiceField(queryset=tester_qset)

    class Meta:
        model = TestResult

class UserStoryShortForm(HiddenHttpRefererForm):
    class Meta:
        model = UserStory
        fields = 'name', 'description'

class ProjectForm(HiddenHttpRefererForm):
    class Meta:
        model = Project

class TaskField(forms.IntegerField):
    def clean(self, value):
        value = super(TaskField, self).clean(value)
        return Task.objects.get(id=value)

def gen_TaskLogForm(user):
    from django.db import connection
    cur = connection.cursor()

    me = user.id
    today = datetime.date.today()
    recent_task = (today - datetime.timedelta(days = 3)).strftime('%Y-%m-%d')
    last_end = (today - datetime.timedelta(days = 7)).strftime('%Y-%m-%d')
    today = today.strftime('%Y-%m-%d')

    menu = TaskHierarchy(None)
    menu['recent'].name =_( 'Recent') 
    menu['mine'].name =_( 'My tasks') 
    menu['inprogress'].name =_( 'In progress') 
    
    projectmenus = []
    
    projects_sql = """
        select distinct
            p.id,   p.name
        from agilito_project p
        join agilito_projectmember pm on pm.project_id = p.id and pm.user_id = %(me)d
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
        join agilito_projectmember pm on pm.project_id = p.id and pm.user_id = %(me)d
        join agilito_iteration i on i.project_id = p.id
        join agilito_userstory us on us.project_id = p.id and us.iteration_id = i.id
        join agilito_task t on t.user_story_id = us.id
        left join agilito_tasklog tlr on tlr.task_id = t.id and tlr.iteration_id = i.id and tlr.date >= '%(recent_task)s'
        left join agilito_tasklog tlm on tlm.task_id = t.id and tlm.iteration_id = i.id and tlm.owner_id = pm.user_id
        where i.start_date <= '%(today)s' and i.end_date >= '%(last_end)s'
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
        date = forms.DateField(required=False)
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
                                        'http_referer']

    return TaskLogForm
