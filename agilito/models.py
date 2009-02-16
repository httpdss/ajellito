from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from django.db.models import Q

from tagging.fields import TagField
import tagging
from tagging.utils import parse_tag_input

from dateutil.rrule import rrule, DAILY, MO, TU, WE, TH, FR
import datetime

# We are using our own search application here!
from queryutils.queryutils import SearchEqualOp, SearchQueryGenerator

# Auxiliary functions.
def _if_is_none_else(item,  rv_case_none,  fun_case_not_none=None):
    if item is None:
        return rv_case_none
    elif fun_case_not_none is None:
        return item
    else:
        return fun_case_not_none(item)

class FieldChoices:
    def __init__(self, *args, **kwargs):
        self.__choices = []

        for c in args:
            k = c[1].replace(' ', '_').upper()
            setattr(self, k, c[0])
            self.__choices.append(c)

        for k in kwargs.keys():
            k = k.upper()
            if hasattr(self, k):
                raise Exception('Duplicate key %s' % k)

            setattr(self, k, kwargs[k][0])
            self.__choices.append(kwargs[k])

    def choices(self):
        return self.__choices

    def label(self, value):
        return filter(lambda x: x[0] == value, self.__choices)[0][1]

class NoProjectException(Exception):
    pass

PERMLINK_PREFIX = __name__.rsplit('.', 1)[0] + '.views.'

class ClueModel(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    class Meta:
        # mondo weird way of doing this, heh
        abstract = True

    @classmethod
    def query(klass, qstatement, project_id=None):
        grammar = { 'name' : SearchEqualOp('name__icontains'),
                    'description': SearchEqualOp('description__icontains'),
                    'id': SearchEqualOp(('id', int, 0))
                  }
        sg = SearchQueryGenerator(grammar, 'name', klass)
        if project_id is not None:
            field_names = klass._meta.get_all_field_names()
            if 'project' in field_names:
                initial_set = klass.objects.filter(project__id=project_id)
            else:
                # I *could* query klass._meta and thus disocver a
                # relation to project and filter on that, but it
                # sounds complicated, delicate, and probable YAGNI.
                # right now, the only subclasses that haven't got a
                # project_id have a user_story :)
                # (same applies to get_absolute_url, below)
                if 'user_story' not in field_names:
                    raise NotImplementedError, \
                        "I don't know how to search on that yet, it seems"
                initial_set = klass.objects.filter(user_story__project__id=project_id)
            return sg.make_query(qstatement, init_q_set=initial_set)
        return sg.make_query(qstatement)
    
    @models.permalink
    def get_absolute_url(self):
        # same comment here as for query and finding project id
        pid = getattr(self, 'project_id', None)
        name = self._meta.module_name
        data = {name + '_id': self.id}
        if pid is None:
            pid = self.user_story.project_id
            data['userstory_id'] = self.user_story.id
        data['project_id'] = pid
        rv = PERMLINK_PREFIX + name + '_detail', (), data
        return rv

    def get_container_model(self):
        raise NotImplementedError,  \
            "I don't know who my container is?"

    def get_container_url(self):
        container = self.get_container_model()
        if not (container is None):        
            return container.get_absolute_url()
        else:
            return None

# Create your models here.
class Project(ClueModel):
    project_members = models.ManyToManyField(User, null=True, blank=True)

    def __unicode__(self):
        return u'P%s: %s' % (self.id, self.name)

    class Meta:
        permissions = (
            ('view', 'Can view the project.'),
        )
        ordering = ('id',)

    def get_absolute_url(self):
        return '/%s/backlog/' % self.id

    @classmethod
    def get_current_project(klass):
        return klass.objects.all()[0]
    
class Release(ClueModel):
    project = models.ForeignKey(Project)
    

    def __unicode__(self):
        return u'RE%s: %s' % (self.id, self.name)

    class Meta:
        permissions = (
            ('view', 'Can view the project.'),
        )

    def get_container_model(self):
        return self.project

class Iteration(ClueModel):
    start_date = models.DateField()
    end_date = models.DateField()

    release = models.ForeignKey('Release', null=True, blank=True)
    project = models.ForeignKey('Project')

    def __unicode__(self):
        return u"IT%s: %s" % (self.id, self.name)

    @models.permalink
    def get_absolute_url(self):
        return 'iteration_status_with_id', (), {'project_id': self.project.id,
                                                'iteration_id': self.id }
                                                
    @property
    def us_accepted(self):
        return sum(us.planned or 0 for us in self.userstory_set.filter(Q(state=UserStory.STATES.ACCEPTED)))
    
    @property
    def us_accepted_percentage(self):
        total = sum(us.planned or 0 for us in self.userstory_set.all())
        accepted = self.us_accepted
        if total <> 0:
            return (float(accepted)/float(total))*100 
        else:
            return 0

    def day_number(self, date):
        """
        Return the day of the iteration we're on.
        date is start-of-day.
        """
        until = min(self.end_date + datetime.timedelta(1), date) - datetime.timedelta(1)
        return rrule(DAILY, cache=True,
                     dtstart=self.start_date, until=until,
                     byweekday=(MO,TU,WE,TH,FR)).count()

    def total_days(self):
        return self.day_number(self.end_date + datetime.timedelta(1))

    def ideal_hours(self, date):
        # the ideal hours results by dividing the estimated hours
        # (which are not changeable except through the admin) evenly
        # over the iteration days
        # date is start-of-day date
        estimated = self.total_estimated()
        ndays = self.total_days()
        elapsed = self.day_number(date)
        return estimated - estimated * elapsed / ndays

    def remaining_hours(self, date):
        return sum(t.remaining_for_date(date)
                   for t in Task.objects.filter(user_story__iteration=self))

    def remaining_storypoints(self, date):
        left = {}
        firstday = ((date - self.start_date).days == 0)
        for us in UserStory.objects.filter(iteration=self):
            if firstday:
                if not us.size:
                    left[us.id] = 1
                else:
                    left[us.id] = us.size
            else:
                left[us.id] = 0

            for t in Task.objects.filter(user_story=us):
                if t.remaining_for_date(date) > 0:
                    left[us.id] = us.size
                    if not left[us.id]:
                        left[us.id] = 1
                    break

        return sum(left.values())

    def total_estimated(self):
        return sum(t.estimate or 0
                   for t in Task.objects.filter(user_story__iteration=self))

    def user_estimated(self, userid):    
        tasks = Task.objects.filter(owner__id=userid, user_story__iteration__pk=self.id)
        return sum(t.estimate or 0 for t in tasks)

    def user_progress(self, userid):
        tasklogs = self.tasklog_set.filter(owner__id=userid)
        return sum(tl.time_on_task or 0 for tl in tasklogs)

    def burndown_data(self):
        burndown = []
        today = datetime.date.today()
        rr = list(rrule(DAILY, cache=True,
                        dtstart=self.start_date, until=self.end_date,
                        byweekday=(MO,TU,WE,TH,FR)))
        rr.append(rr[-1] + datetime.timedelta(1))
        for i, a_datetime in enumerate(rr):
            a_date = a_datetime.date()
            data = dict(day=i,
                        ideal=self.ideal_hours(a_date))
            if a_date > today:
                data['remaining'] = None
                data['remaining_storypoints'] = None
            else:
                data['remaining'] = self.remaining_hours(a_date)
                data['remaining_storypoints'] = self.remaining_storypoints(a_date)

            burndown.append(data)
        return burndown

    def story_cards(self):
        cards = []
        for us in UserStory.objects.filter(iteration=self):
            card = {}
            card['StoryID'] = us.id
            card['StoryName'] = us.name
            card['StoryDescription'] = us.description
            card['StoryRank'] = _if_is_none_else(us.relative_rank, '?')
            card['StorySize'] = _if_is_none_else(us.size, '?', lambda s: UserStory.SIZES.label(s))
            cards.append(card)
        return cards

    def task_cards(self):
        cards = []
        for t in Task.objects.filter(user_story__iteration=self):
            card = {}
            card['TaskID'] = t.id
            card['TaskName'] = t.name
            card['TaskDescription'] = t.description
            card['TaskEstimate'] = _if_is_none_else(t.estimate, '?')
            card['TaskRemaining'] = _if_is_none_else(t.remaining, '?')
            card['TaskOwner'] = _if_is_none_else(t.owner, 'Unassigned', lambda u: u.username)
            card['TaskTags'] = t.tags

            us = t.user_story

            card['StoryID'] = us.id
            card['StoryName'] = us.name
            card['StoryDescription'] = us.description
            card['StoryRank'] = _if_is_none_else(us.relative_rank, '?')

            cards.append(card)
        return cards

    @property
    def estimated_without_owner(self):
        tasks = Task.objects.filter(owner=None, user_story__iteration__pk=self.id)
        return sum(tl.estimate or 0 for tl in tasks)


    @property
    def users_total_status(self):
        users = self.project.project_members.all()
        out = []
        for u in users:
            out.append({
                'name': u.username,
                'estimated': self.user_estimated(u.id),
                'progress': self.user_progress(u.id),
            })
        out.append({
            'name': 'no owner',
            'estimated':self.estimated_without_owner,
            'progress': '',
        })
        return out

    def get_container_model(self):
        if self.release is None:
            return self.project
        return self.release
        
    class Meta:
        permissions = (
            ('view', 'Can view the iteration.'),
        )
        ordering = ('-id',)

class UserStoryAttachment(ClueModel):
    attachment = models.FileField(upload_to='attachments/')

    user_story = models.ForeignKey('UserStory')

    def __unicode__(self):
        return self.name

    def get_container_model(self):
        return self.user_story

    class Meta:
        verbose_name = _(u'US Attachment')
        verbose_name_plural = _(u'US Attachments')

        permissions = (
            ('view', 'Can view the user stories.'),
        )

class UserStory(ClueModel):
    STATES = FieldChoices(
                (1, 'Archived'),
                (10, 'Defined'),
                (15, 'Specified'),
                (20, 'In Progress'),
                (30, 'Completed'),
                (40, 'Accepted'))

    SIZES = FieldChoices(
                (1,  'XXS'),
                (2,  'XS'),
                (3,  'S'),
                (5,  'M'),
                (8,  'L'),
                (13, 'XL'),
                (21, 'XXL'),
                (1000,  'Too large'))

    project = models.ForeignKey(Project)

    planned = models.SmallIntegerField(null=True, blank=True)
    iteration = models.ForeignKey(Iteration, null=True, blank=True)
    rank = models.IntegerField(null=True, blank=True)

    state = models.SmallIntegerField(choices=STATES.choices(), default=STATES.DEFINED)

    # alter table agilito_userstory add column size smallint
    size = models.SmallIntegerField(choices=SIZES.choices(), null=True)

    # alter table agilito_userstory add column created date NOT NULL default 'now',
    # alter table agilito_userstory add column closed date
    created = models.DateField(default=datetime.datetime.now())
    closed = models.DateField(null=True)

    def __unicode__(self):
        return u'US%s: %s' % (self.id, self.name)

    @property
    def is_blocked(self):
        return (Impediment.objects.filter(resolved=None, tasks__user_story=self).count() != 0)

    @property
    def is_pinned(self):
        # eeh: this might need refinement. I was considering making an
        # object pinned when it is assigned to an iteration, but that
        # would duplicate stories even if you accidently set the wrong
        # iteration. Best to let the user choose. Stuff that has seen
        # work (= tasklogs) should be considered in-use though.
        return (TaskLog.objects.filter(task__user_story=self).count() != 0)

    @property
    def relative_rank(self):
        if self.iteration is None or self.rank is None:
            return None

        return UserStory.objects.filter(iteration=self.iteration, rank__lt=self.rank).count() + 1

    @property
    def estimated(self):
        return sum(t.estimate for t in self.task_set.all() if t.estimate and not t.is_archived)

    @property
    def actuals(self):
        return sum(t.actuals for t in self.task_set.all() if t.actuals and not t.is_archived)

    @property
    def remaining(self):
        if self.is_archived:
            return 0
        return sum(t.remaining for t in self.task_set.all() if t.remaining and not t.is_archived)

    @classmethod
    def backlogged(klass, project):
        return klass.objects.filter(project__id=project, iteration=None).exclude(state=UserStory.STATES.ARCHIVED).order_by('rank')

    @property
    def test_failed(self):
        testcases = self.testcase_set.all()
        out = 0
        for t in testcases:
            try:
                tf = t.testresult_set.latest()
                if tf.result<>1:
                    out +=1
                
            except TestResult.DoesNotExist:
                pass
               
        return out

    @property
    def is_archived(self):
        return (self.state == UserStory.STATES.ARCHIVED)

    def copy_to_iteration(self, iteration, copy_tasks, archiver):
        id = self.id

        tasks = self.task_set.all()

        self.id = None
        self.iteration=iteration
        self.state = UserStory.STATES.DEFINED
        self.created = datetime.datetime.now()
        self.closed = None
        self.save()

        if copy_tasks:
            for task in tasks:
                task.id = None
                task.user_story = self
                task.estimate = task.remaining
                task.state = Task.STATES.DEFINED
                task.save()

        if archiver:
            story = UserStory.objects.get(id=id)
            story.archive(archiver)

    def archive(self, archiver):
        for task in self.task_set.all():
            task.archive(archiver)

        self.state = UserStory.STATES.ARCHIVED
        self.closed = datetime.date.today()
        self.save()

    def get_container_model(self):
        return self.iteration

    def get_container_url(self):
        if self.iteration is None:
            return '/%s/backlog' % self.project.id         
        else:
            return self.iteration.get_absolute_url()

    @property
    def tasks(self):
        return Task.objects.filter(user_story=self)

    class Meta:
        verbose_name = _(u'User Story')
        verbose_name_plural = _(u'User Stories')

        permissions = (
            ('view', 'Can view the user stories.'),
        )

        ordering = ('rank', 'id')

    def save(self):
        from django.db import connection
        cursor = connection.cursor()
        if not self.id is None:
            cursor.execute('select rank from agilito_userstory where id=%s', (self.id,))
            rank = cursor.fetchone()[0]
            if not rank is None:
                cursor.execute('update agilito_userstory set rank = rank - 1 where project_id=%s and rank > %s', (self.project_id,rank))
        if not self.rank is None:
            cursor.execute("""
                update agilito_userstory set rank = rank + 1 where project_id=%s and not rank is null and rank >= %s
                """, (self.project_id, self.rank))

        super(UserStory, self).save()


class UserProfile(models.Model):
    CATEGORIES = FieldChoices(
                    (10, 'Client'),
                    (20, 'Project Manager'),
                    (30, 'Developer'),
                    (40, 'Designer'),
                    (50, 'Tester'),
                    (99, 'Other'))

    hours_per_week = models.SmallIntegerField()
    category = models.SmallIntegerField(choices=CATEGORIES.choices())
    user = models.ForeignKey(User, unique=True)
    
    def __unicode__(self):
        return u'%s: %s' % (self.user.username, self.get_category_display())

    @property
    def capacity(self):
        raise NotImplementedError

    class Meta:
        verbose_name = _(u'User Profile')
        verbose_name_plural = _(u'User Profiles')

class Task(ClueModel):
    STATES = FieldChoices(
                (1, 'Archived'),
                (10, 'Defined'),
                (20, 'In Progress'),
                (30, 'Completed'))

    CATEGORIES = FieldChoices(
                ( 0, 'Undefined'),
                (10, 'UI'),
                (20, 'Design'),
                (30, 'Development'),
                (40, 'Testing'),
                (99, 'Other'))

    estimate = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    remaining = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)

    state = models.SmallIntegerField(choices=STATES.choices(), default=STATES.DEFINED)

    category = models.SmallIntegerField(choices=CATEGORIES.choices(), default=CATEGORIES.UNDEFINED)

    owner = models.ForeignKey(User, blank=True, null=True)
    user_story = models.ForeignKey('UserStory')

    # alter table agilito_task add column tags varchar(255) NOT NULL default ''
    tags = TagField()

    @property
    def taglist(self):
        return parse_tag_input(self.tags)

    @property
    def is_blocked(self):
        return (Impediment.objects.filter(resolved=None, tasks=self).count() != 0)

    @property
    def actuals(self):
        return sum(i.time_on_task for i in self.tasklog_set.all())

    @property
    def is_complete(self):
        return (self.state == Task.STATES.COMPLETED)

    @property
    def is_archived(self):
        return (self.state == Task.STATES.ARCHIVED)

    @property
    def is_in_progress(self):
        return (self.state == Task.STATES.IN_PROGRESS)

    @property
    def is_defined(self):
        return (self.state == Task.STATES.DEFINED)

    def archive(self, archiver):
        tasklog = TaskLog()
        tasklog.task = self
        tasklog.time_on_task = 0
        tasklog.summary = 'Archived'
        tasklog.date = datetime.datetime.now()
        tasklog.iteration = self.user_story.iteration
        tasklog.owner = archiver
        tasklog.old_remaining = self.remaining
        tasklog.save()

        self.state = Task.STATES.ARCHIVED
        self.remaining = 0
        self.save()

    def remaining_for_date(self, date):
        # find the oldest tasklog that is newer than date and check
        # what the estimate on this task was then
        try:
            log = self.tasklog_set.filter(date__gt=date).order_by('date')[0:1].get()
        except TaskLog.DoesNotExist:
            # no tasklog between here and there
            return self.remaining or 0
        else:
            if log.old_remaining is not None:
                return log.old_remaining
            else:
                # the info isn't there :(
                # return something almost but not quite useful
                return self.estimate or 0

    def __unicode__(self):
        return u'TA%s: %s' % (self.id, self.name)

    def get_container_model(self):
        return self.user_story

    class Meta:
        permissions = (
            ('view', 'Can view the task.'),
        )
        ordering = ('user_story__rank', 'user_story__id', 'id')

class TestCase(ClueModel):
    KINDS = FieldChoices(
                (10, 'Acceptance'),
                (20, 'Functional'),
                (99, 'Other'))

    PRIORITIES = FieldChoices(
                (10, 'Useful'),
                (20, 'Important'),
                (30, 'Critical'))

    user_story = models.ForeignKey('UserStory')

    priority = models.SmallIntegerField(choices=PRIORITIES.choices(),
                                        null=True, blank=True, default=20)
    precondition = models.TextField(blank=True)
    steps = models.TextField(blank=True)
    postcondition = models.TextField(blank=True)

    def __unicode__(self):
        return u'TC%s: %s' % (self.id, self.name)

    def get_container_model(self):
        return self.user_story

    class Meta:
        verbose_name = _(u'Test Case')
        verbose_name_plural = _(u'Test Cases')

        ordering = ('-priority',)

        permissions = (
            ('view', 'Can view the test cases.'),
        )
#tagging.register(Task)

class TestResult(models.Model):
    RESULTS = FieldChoices(
                (0, 'Fail'),
                (1, 'Pass'),
                (2, 'Error'),
                (3, 'Inconclusive'))

    result = models.SmallIntegerField(choices=RESULTS.choices())
    comments = models.TextField(blank=True)
    date = models.DateTimeField()
    tester = models.ForeignKey(User)
    test_case = models.ForeignKey(TestCase)

    def __unicode__(self):
        return u'TR%s: [%s, %s, %s, %s]' % (self.id,
                                            self.test_case,
                                            self.date,
                                            self.tester.username,
                                            self.result,)

    @models.permalink
    def get_absolute_url(self):
        return 'testresult_detail_with_id', (), {'project_id': self.test_case.user_story.project.id,
                                                 'userstory_id': self.test_case.user_story.id,
                                                 'testcase_id' : self.test_case.id,
                                                 'testresult_id': self.id,
                                                }      

    def get_container_model(self):
        return self.test_case
    
    def get_container_url(self):
        return self.test_case.get_absolute_url()

    class Meta:
        ordering = ('-date',)        
        
        get_latest_by = 'date'        

        verbose_name = _(u'Test Result')
        verbose_name_plural = _(u'Test Results')

        permissions = (
            ('view', 'Can view the test results.'),
        )

class Impediment(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    opened = models.DateField(default=datetime.datetime.now())
    resolved = models.DateTimeField(null=True)

    tasks = models.ManyToManyField('Task')

    @models.permalink
    def get_absolute_url(self):
        it = self.tasks.all()[0].user_story.iteration

        return PERMLINK_PREFIX + 'impediment_edit', (), {'project_id': it.project.id, 'iteration_id': it.id, 'impediment_id': self.id }

    class Meta:
        ordering = ('-opened',)        
        
        verbose_name = _(u'Impediment')
        verbose_name_plural = _(u'Impediments')

        permissions = (
            ('view', 'Can view the impediments.'),
        )

class TaskLog(models.Model):
    task = models.ForeignKey('Task')
    time_on_task = models.DecimalField(max_digits=5, decimal_places=2)
    summary = models.TextField()
    date = models.DateTimeField()
    iteration = models.ForeignKey('Iteration', null=True)
    owner = models.ForeignKey(User)
    old_remaining = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)


    def __unicode__(self):
        return 'Task Log: [%s, %s, %s, %s, %s]' % (self.iteration, self.date, 
                                                   self.task,
                                                   self.time_on_task,
                                                   self.owner.username)

    @property
    def project(self):
        return self.iteration.project

    def get_container_model(self):
        return self.task

    def get_container_url(self):
        return self.task.get_absolute_url()

    def get_csv_row(self):

        pr = self.task.user_story.project
        it = self.task.user_story.iteration
        us = self.task.user_story

        return [self.date,
                "%s" % pr.name.encode('utf8'),
                "%s" % _if_is_none_else(it, 'Backlog', lambda x : x.name.encode('utf8')),
                "%s" % us.name.encode('utf8'),
                "%s" % self.task.name.encode('utf8'),
                self.owner.username,
                self.time_on_task,
                "%s" % self.summary.encode('utf8'),
               ]

    class Meta:
        verbose_name = _(u'Task Log')
        verbose_name_plural = _(u'Task Logs')
        get_latest_by = 'date'

        permissions = (
            ('view', 'Can view the task log.'),
        )

