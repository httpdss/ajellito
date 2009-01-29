from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from django.db.models import Q

from dateutil.rrule import rrule, DAILY, MO, TU, WE, TH, FR
import datetime

# We are using our own search application here!
from queryutils.queryutils import SearchEqualOp, SearchQueryGenerator

# Auxiliary functions.
def _if_is_none_else(item,  rv_case_none,  fun_case_not_none):
    if item is None:
        return rv_case_none
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
        return filter(lambda x: x[0] == value, self.__choices)[1]

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
        for us in UserStory.objects.filter(iteration=self):
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
            card['StoryRank'] = us.rank
            card['StorySize'] = us.planned
            cards.append(card)
        return cards

    def task_cards(self):
        cards = []
        for t in Task.objects.filter(user_story__iteration=self):
            card = {}
            card['TaskID'] = t.id
            card['TaskName'] = t.name
            card['TaskDescription'] = t.description
            card['TaskEstimate'] = t.estimate

            us = t.user_story

            card['StoryID'] = us.id
            card['StoryName'] = us.name
            card['StoryDescription'] = us.description
            card['StoryRank'] = us.rank

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
    blocked = models.BooleanField(default=False)

    # alter table agilito_userstory add column size smallint
    size = models.SmallIntegerField(choices=SIZES.choices(), null=True)

    def __unicode__(self):
        return u'US%s: %s' % (self.id, self.name)

    @property
    def estimated(self):
        return sum(i.estimate for i in self.task_set.all()
                   if i.estimate)

    @property
    def actuals(self):
        return sum(i.actuals for i in self.task_set.all()
                   if i.actuals)

    @property
    def remaining(self):
        return sum(i.remaining for i in self.task_set.all()
                   if i.remaining)

    @classmethod
    def backlogged(klass, project):
        return klass.objects.filter(project__id=project, iteration=None).exclude(state=1).order_by('rank')

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

    def archive(self):
        self.state = UserStory.STATES.ARCHIVED
        self.save()

    def get_container_model(self):
        return self.iteration

    def get_container_url(self):
        if self.iteration is None:
            return '/%s/backlog' % self.project.id         
        else:
            return self.iteration.get_absolute_url()

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
                (30, 'Complete'))

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

    @property
    def actuals(self):
        return sum(i.time_on_task for i in self.tasklog_set.all())

    @property
    def is_complete(self):
        return (self.state == Task.STATES.COMPLETE)

    @property
    def is_archived(self):
        return (self.state == Task.STATES.ARCHIVED)

    @property
    def is_in_progress(self):
        return (self.state == Task.STATES.IN_PROGRESS)

    @property
    def is_defined(self):
        return (self.state == Task.STATES.DEFINED)

    def archive(self):
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

