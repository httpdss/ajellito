from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from django.db.models import Q
from django.core.cache import cache
from django.db.models.signals import post_save, post_delete

from tagging.fields import TagField
import tagging
from tagging.utils import parse_tag_input
from decimal import Decimal
from collections import defaultdict
from django.core.urlresolvers import reverse
from tagging.utils import parse_tag_input

from dateutil.rrule import rrule, DAILY, MO, TU, WE, TH, FR
import datetime, time
import math, re
import sys
import inspect

from agilito import CACHE_ENABLED, UNRESTRICTED_SIZE, CACHE_PREFIX

class Object(object):
    def __init__(self, *args, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def _(self, name):
        if hasattr(self, name):
            raise AttributeError("Won't auto-create attribute %s" % name)
        o = Object()
        setattr(self, name, o)
        return o

    @staticmethod
    def _clean(obj, cache=[]):
        if obj in cache:
            return

        if isinstance(obj, Object):
            try:
                del obj.tmp
            except AttributeError:
                pass

            for n, o in obj.__dict__.items():
                Object._clean(o, cache + [obj])
        elif isinstance(obj, list):
            for o in obj:
                Object._clean(o, cache + [obj])
        elif isinstance(obj, (dict, defaultdict)):
            for o in obj.values():
                Object._clean(o, cache + [obj])

    def clean(self):
        Object._clean(self)
        return self

    def __str__(self):
        return '[' + ', '.join(['%s: %s' % (n, str(v)) for (n, v) in self.__dict__.items()]) + ']'

def same_date(d1, d2):
    return ((d1 - d2).days == 0)

def invalidate_cache(sender, instance, **kwargs):
    ids = []

    if isinstance(instance, User):
        ids = [p.id for p in instance.project_set.all()]
    elif hasattr(instance, 'project'):
        ids = [instance.project.id]

    for id in ids:
        Project.touch_cache(id)

if CACHE_ENABLED:
    post_save.connect(invalidate_cache, weak=False)
    post_delete.connect(invalidate_cache, weak=False)

def cached(f):
    def f_cached(*args, **kwargs):
        global CACHE_ENABLED

        self = args[0]
        if not CACHE_ENABLED or not hasattr(self, 'project_id'):
            return f(*args, **kwargs)

        params = f.func_code.co_varnames[:f.func_code.co_argcount]
        vardict = dict(zip(params, ['<None>' for d in params]))
        vardict.update(dict(zip(f.func_code.co_varnames, args)))
        vardict.update(kwargs)
        # replace 'self' with module:class:id:method 
        obj = '%s.%s.%s(%s' % (self.__class__.__module__, self.__class__.__name__, f.__name__, str(self.id))
        vardict['self'] = obj

        pv = Project.cache_id(self.project_id)

        key = CACHE_PREFIX + '.'
        key += ','.join([str(vardict[v]) for v in params]) + ')'
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
        self.__hidden_choices = []
        self.keys = []

        for v, l in args:
            k = re.sub('[^_A-Za-z0-9]', '', l.replace(' ', '_'))

            self.addkey(k, v, l)

        for k in kwargs.keys():
            v, l = kwargs[k]
            self.addkey(k, v, l)

        self.keys = [v[0] for v in self.__choices]

    def addkey(self, k, v, l):
        if hasattr(self, k):
            raise Exception('Duplicate key "%s" for (%s, %s)' % (k, v, l))
        if l.startswith('#'):
            self.__hidden_choices.append((v, l[1:]))
        else:
            self.__choices.append((v, l))
        setattr(self, k.upper(), v)

    def choices(self, include_hidden = False):
        if include_hidden:
            return self.__choices + self.__hidden_choices
        return self.__choices

    def values(self, include_hidden = False):
        return [c[0] for c in self.choices(include_hidden)]

    def label(self, value):
        if value is None:
            return None
        return filter(lambda x: x[0] == value, self.__choices + self.__hidden_choices)[0][1]

class NoProjectException(Exception):
    pass

PERMLINK_PREFIX = __name__.rsplit('.', 1)[0] + '.views.'

class ClueModel(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    @property
    def whatami(self):
        return self.__class__.__name__

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

    @property
    def project(self):
        return self

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

    @classmethod
    def touch_cache(klass, id):
        now = datetime.datetime.now()
        midnight = now.replace(hour=23, minute=59, second=59, microsecond=0)
        delta = midnight - now

        v = str(time.time())
        cache.set('%s.project-cache-version-%s' % (CACHE_PREFIX, id), v, delta.seconds)
        return v

    @classmethod
    def cache_id(klass, id):
        v = cache.get('%s.project-cache-version-%s' % (CACHE_PREFIX, id))
        if not v:
            return Project.touch_cache(id)
        return v

    @staticmethod
    def backlog_cmp_rank(self, other):
        if self.rank is None and not other.rank is None:
            return 1
        if not self.rank is None and other.rank is None:
            return -1
        if self.rank is None and other.rank is None:
            return cmp(self.typerank, other.typerank)
        return cmp(Decimal('%d.%d' % (self.rank, self.typerank)), Decimal('%d.%d' % (other.rank, other.typerank)))

    @cached
    def backlog_suggest(self, states, base):
        backlog = self.backlog(states)
        suggestions, accuracy = self.suggested_sizes(states, base)

        backlog._('suggestions').accuracy = 100 * accuracy
        backlog.suggestions.base = base

        for story in backlog.backlog:
            if story.whatami != 'UserStory':
                continue

            try:
                story.suggestion = suggestions[story.id]
            except KeyError:
                story.suggestion = None
        return backlog

    @cached
    def backlog(self, states):
        from django.db import connection, transaction
        cursor = connection.cursor()

        result = Object()

        cursor.execute("""
            select avg(end_date - start_date)
            from agilito_iteration
            where project_id = %s""", (self.id,))
        try:
            l = int(cursor.fetchone()[0])
        except TypeError:
            l = None
        result._('velocity').sprint_length = None

        stateset = ','.join([str(s) for s in states])

        ## this selects all stories that are part of an iteration that
        ## has no unsized stories, all stories have at least one task,
        ## and no tasks are unestimated. As all iterations should be.
        cursor.execute("""
            select
                sum(s.size) as planned,
                sum(case when s.state=%s then s.size else 0 end) as finished
            from agilito_userstory s
            where s.project_id = %s and s.iteration_id in 
                (select i.id
                from agilito_iteration i
                where project_id = %s
                and not exists (select 1
                    from agilito_userstory s
                    left join agilito_task t on t.user_story_id = s.id
                    where s.iteration_id = i.id and (s.size is NULL or t.estimate is NULL)
                    )
                )
        """, (UserStory.STATES.ACCEPTED, self.id, self.id))

        result.velocity.actual, result.velocity.planned = cursor.fetchone()

        if result.velocity.planned:
            result.velocity.accuracy = float(result.velocity.actual) / result.velocity.planned
        else:
            result.velocity.accuracy = None

        if result.velocity.actual and result.velocity.sprint_length:
            points_per_day = float(result.velocity.actual / result.velocity.sprint_length)
        else:
            points_per_day = 0

        today = datetime.date.today()
        stories = []
        cursor.execute("""
            select s.id, s.size, s.rank, s.name, s.description, s.state, s.tags, i.name
                , case when s.state = %s then 'accepted'
                    when s.state = %s then 'failed'
                    when s.state = %s and i.id is NULL then 'needs-work'
                    when i.id is NULL then 'unplanned'
                    when i.start_date >= %s then 'planned'
                    when i.end_date < %s then 'forgotten'
                    when i.end_date >= %s then 'in-progress'
                    else 'unknown' end
            from agilito_userstory s
            left join agilito_iteration i on s.iteration_id = i.id
            where s.project_id = %s and s.state in (""" + stateset + ')', (
                    UserStory.STATES.ACCEPTED,
                    UserStory.STATES.FAILED,
                    UserStory.STATES.DEFINED,
                    today, today, today, self.id))
        for id, size, rank, name, description, state, tags, iteration_name, backlog_state in cursor.fetchall():
            story = Object(typerank=1, id=id, size=size, rank=rank, name=name, description=description, state=state,
                           backlog_state=backlog_state, whatami = 'UserStory')
            story.get_absolute_url = reverse('agilito.views.userstory_detail', args=[self.id, id])
            if iteration_name:
                story._('iteration').name = iteration_name
            else:
                story.iteration = None
            story.taglist = parse_tag_input(tags)
            stories.append(story)

        cursor.execute("""
            select count(1), sum(size)
            from agilito_userstory
            where project_id=%s and state in (""" + stateset + ')', (self.id,))
        result.story_count, result.size = cursor.fetchone()

        cursor.execute("""
            select min(rank)
            from agilito_userstory
            where project_id = %s and state in (""" + stateset + ')', (self.id,))
        minrank = cursor.fetchone()[0]

        # make sure at least one story is shown before the first shown
        # release
        if minrank is None:
            minrank = ''
        else:
            minrank = ' and r.rank >= %d' % minrank

        release_by_id = {}
        cursor.execute("""
            select r.id, r.name, r.deadline, r.rank
            from agilito_release r
            where r.project_id = %s""" + minrank, (self.id,))
        for id, name, deadline, rank in cursor.fetchall():
            release = Object(typerank=0, id=id, name=name, deadline=deadline, rank=rank, whatami='Release')

            if points_per_day == 0:
                release._('release_date').date = None
                release.release_date.error = 'project has unknown velocity'
                release.release_date.severity = 'error'
                release.release_date.achieved = False
            else:
                release._('release_date').date = today
                release.release_date.error = None
                release.release_date.severity = None
                release.release_date.achieved = True

            release_by_id[id] = release

        warn_accuracy = (not result.velocity.accuracy is None and math.fabs(1-result.velocity.accuracy) < 0.1)

        endstates = ','.join([str(s) for s in UserStory.ENDSTATES])
        cursor.execute("""
            select r.id,
                max(i.end_date) as last_iteration_end,
                sum(case when s.size is NULL then 1 else 0 end) as unsized,
                sum(case when s.iteration_id is NULL then 0 else s.size end) as unplanned,
                sum(case when s.state in (""" + endstates + """) then 0 else 1 end) as unfinished
            from agilito_release r
            join agilito_userstory s on s.project_id = r.project_id and s.rank < r.rank
            left join agilito_iteration i on s.iteration_id = i.id
            where r.project_id = %s""" + minrank + """
            group by r.id""", (self.id,))
        for id, it_end, unsized, unplanned, unfinished in cursor.fetchall():
            release = release_by_id[id]
            if unsized or (unplanned and points_per_day == 0):
                release.release_date.date = None
                if unsized:
                    release.release_date.error = 'release has unsized stories'
                else:
                    release.release_date.error = 'project has unknown velocity'
                release.release_date.severity = 'error'
                release.release_date.achieved = False
            else:
                if it_end:
                    release.release_date.date = it_end
                else:
                    release.release_date.date = today

                release.release_date.date += datetime.timedelta(unplanned * points_per_day)

                if release.deadline and release.deadline < release.release_date.date:
                    release.release_date.severity = 'error'
                    release.release_date.error = 'deadline exceeded'
                elif unplanned and warn_accuracy:
                    release.release_date.error = 'sprints based on unproven velocity'
                    release.release_date.severity = 'warning'

        result.backlog = sorted(stories + release_by_id.values(), Project.backlog_cmp_rank)

        return result

    def suggested_sizes(self, states, base):
        from django.db import connection, transaction
        cursor = connection.cursor()

        stateset = ','.join([str(s) for s in states])

        if base=='actuals':
            field = 'tl.time_on_task'
            tasklogs = 'join agilito_tasklog tl on tl.task_id = t.id'
        elif base == 'estimates':
            field = 't.estimate'
            tasklogs = ''
        else:
            raise Exception('Unexpected calculation base "%s"' % base)

        cursor.execute("""
            select count(1)
            from agilito_userstory
            where project_id = %s and state in (""" + stateset + """)
            """, (self.id,))
        stories = cursor.fetchone()[0]

        cursor.execute("""
            select sum(""" + field + """)
            from agilito_userstory s
            join agilito_task t on t.user_story_id = s.id
            """ + tasklogs + """
            where s.project_id = %s and s.state in (""" + stateset + """)
            """, (self.id,))
        estimate = cursor.fetchone()[0]

        avg = estimate / stories

        cursor.execute("""
            select s.id, max(s.size), sum(""" + field + """)
            from agilito_userstory s
            join agilito_task t on t.user_story_id = s.id
            """ + tasklogs + """
            where s.project_id = %s and s.state in (""" + stateset + """)
            group by s.id
            order by abs(sum(t.estimate) - %s)
            """, (self.id, avg))
        benchmark = cursor.fetchone()[1]

        choices = zip(
                    UserStory.SIZES.values() + [UserStory.SIZES.XL + UserStory.SIZES.XXL],
                    UserStory.SIZES.values() + [UserStory.SIZES.INFINITY],
                  )

        benchmark = None
        suggestions = {}
        planned = 0
        suggested = 0
        for id, size, hours in cursor.fetchall():
            story = Object()

            if benchmark is None:
                story.is_benchmark = True
                benchmark = hours
            else:
                story.is_benchmark = False
            story.hours = hours
            size = (story.hours/benchmark) * UserStory.SIZES.M
            story.size = sorted([(math.fabs(size-c), s) for c, s in choices], lambda x, y: cmp(x[0], y[0]))[0][1]

            planned += size
            suggested += story.size
            suggestions[id] = story

        return (suggestions, planned / suggested)

    def reorder_backlog(self, table, id, rank):
        if rank is None:
            return

        from django.db import connection, transaction
        cursor = connection.cursor()

        if rank in ['min', 'max']:
            ranks = []
            for t in ['userstory', 'release']:
                cursor.execute('select %s(rank) from agilito_%s where project_id = %%s' % (rank, t), (self.id,))
                r = cursor.fetchone()[0]
                if not r is None: ranks.append(r)

            if ranks == []:
                rank = 1
            elif rank == 'min':
                rank = min(ranks) - 1
            else:
                rank = max(ranks) + 1

        for t in ['userstory', 'release']:
            cursor.execute('update agilito_%s set rank = rank + 1 where project_id = %%s and rank >= %%s' % t, (self.id, rank))
        cursor.execute('update agilito_%s set rank = %%s where project_id = %%s and id = %%s' % table, (rank, self.id, id))
        transaction.commit_unless_managed()
        # database updates must touch the cache unless they're being done in a 'save' method,
        # which touches the cache using a signal
        Project.touch_cache(self.id)

    def compact_ranks(self):
        from django.db import connection, transaction
        cursor = connection.cursor()

        cursor.execute("""
            select 1 as relorder, 'userstory' as tbl, id, rank from agilito_userstory
                where project_id = %s and not rank is NULL
            union

            select 0, 'release', id, rank from agilito_release
                where project_id = %s and not rank is NULL
            
            order by rank, relorder""", (self.id, self.id))

        objs = [(r[1], r[2]) for r in cursor.fetchall()]
        for rank, obj in enumerate(objs):
            tbl, id = obj
            cursor.execute('update agilito_%s set rank = %%s where id = %%s' % tbl, (rank + 1, id))
        transaction.commit_unless_managed()
        # database updates must touch the cache unless they're being done in a 'save' method,
        # which touches the cache using a signal
        Project.touch_cache(self.id)

class Release(ClueModel):
    project = models.ForeignKey(Project)
    rank = models.IntegerField(null=True, blank=True)
    deadline = models.DateField(null=True, blank=True)

    def __unicode__(self):
        return u'RE%s: %s' % (self.id, self.name)

    class Meta:
        permissions = (
            ('view', 'Can view the project.'),
        )
        ordering = ('rank',)

    def get_container_model(self):
        return self.project

    @models.permalink
    def get_absolute_url(self):
        return 'release_edit', (), {'project_id': self.project.id, 'release_id': self.id }      

    def save(self):
        super(Release, self).save()
        self.project.reorder_backlog('release', self.id, self.rank)

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
                                                
    def user_estimated(self, userid):    
        tasks = Task.objects.filter(owner__id=userid, user_story__iteration__pk=self.id)

        return sum(t.estimate or 0 for t in tasks)

    def user_progress(self, userid):
        tasklogs = self.tasklog_set.filter(owner__id=userid)
        return sum(tl.time_on_task or 0 for tl in tasklogs)

    @cached
    def status(self):
        from django.db import connection
        cursor = connection.cursor()

        result = Object()

        ## determine the days for this iteration
        days = [datetime.date(d.year, d.month, d.day)
                for d in rrule(DAILY,
                               cache=True,
                               dtstart=self.start_date,
                               until=self.end_date,
                               byweekday=(MO,TU,WE,TH,FR))]

        result._('burndown').days = len(days)
        result.burndown.dates = days
        lastday = result.burndown.days - 1
        dayrange = list(xrange(result.burndown.days))

        ## calculate day-within-sprint number from a date
        start_date = self.start_date
        end_date = self.end_date

        date2day = {}
        def getday(dt):
            if isinstance(dt, datetime.datetime):
                dt = datetime.date(dt.year, dt.month, dt.day)
            try:
                return date2day[dt]
            except KeyError:
                if dt <= start_date:
                    d = 0 # note logs for the 1st day on the 2nd day
                elif dt > end_date:
                    d = lastday
                else:
                    for d, wd in enumerate(days):
                        if wd >= dt:
                            break
            date2day[dt] = d
            return d
        today = getday(datetime.date.today())
        activedays = list(xrange(today+1))

        def tasklogday(dt):
            d = getday(dt)
            if d == 0: return 1
            if d >= today or d >= lastday: return min(today, lastday) - 1
            return d - 1

        project_id = self.project.id

        result.stories = []
        result.tags = defaultdict(list)
        result.time_spent = 0
        result.size = 0
        result.hours = 0

        stories_by_id = {}
        tasks_by_id = {}

        ## fetch story data
        unranked = []
        accepted = 0
        cursor.execute("""select s.id, s.name, s.description, s.state, s.size, s.rank, s.tags
                          from agilito_userstory s
                          where s.iteration_id = %s
                          order by rank""", (self.id,))
        for id, name, description, state, size, rank, tags in cursor.fetchall():
            story = Object(id=id, name=name, description=description, state=state, size=size, rank=rank,  whatami='UserStory')
            story.get_absolute_url = reverse('agilito.views.userstory_detail', args=[project_id, id])
            story.taglist = parse_tag_input(tags)
            story.is_blocked = False
            story.tasks = []
            story.time_spent = 0
            result.size += size or 0
            if story.state == UserStory.STATES.ACCEPTED:
                accepted += 1

            story._('tmp').hours_remaining_for_day = [None for day in activedays]
            story.tmp.points_remaining_for_day = [None for day in activedays]
            story.tmp.testresult = {}

            for tag in story.taglist:
                result.tags[tag].append(story)

            stories_by_id[id] = story

            if rank is None:
                unranked.append(story)
            else:
                result.stories.append(story)
        ## this makes sure unranked stories go to the bottom
        result.stories.extend(unranked)

        if len(result.stories) != 0:
            result.stories_accepted_percentage = (accepted * 100.0) / len(result.stories)
        else:
            result.stories_accepted_percentage = 0

        ## compact ranks within a sprint
        for rank, story in enumerate(result.stories):
            story.relative_rank = rank + 1

        ## fetch story test failures
        cursor.execute("""
            select us.id, tc.id, tr.result
            from agilito_userstory us
            join agilito_testcase tc on tc.user_story_id = us.id
            join agilito_testresult tr on tr.test_case_id = tc.id
            where us.iteration_id =%s
            order by tr.date""", (self.id,))
        for storyid, tcid, testresult in cursor.fetchall():
            try:
                tr = stories_by_id[storyid].tmp.testresult
            except KeyError:
                continue
            if testresult == TestResult.RESULTS.Pass:
                tr[tcid] = 0
            else:
                tr[tcid] = 1

        result.failures = 0
        for story in result.stories:
            story.failures = sum(r for r in story.tmp.testresult.values())
            result.failures += story.failures

        ## fetch task data
        task_owner = {None: None}
        cursor.execute("""select t.id, t.name, t.description, t.state, t.estimate, t.remaining, t.tags, t.user_story_id, u.username, u.first_name, u.last_name, u.email
                          from agilito_task t
                          join agilito_userstory s on s.id = t.user_story_id
                          left join auth_user u on t.owner_id = u.id
                          where s.iteration_id = %s
                          order by t.id
                          """, (self.id,))
        for id, name, description, state, estimate, remaining, tags, user_story_id, username, first_name, last_name, email in cursor.fetchall():
            try:
                story = stories_by_id[user_story_id]
            except KeyError:
                continue
            task = Object(id=id, name=name, description=description, estimate=estimate, state=state, remaining=remaining, whatami='Task')
            task.get_absolute_url = reverse('agilito.views.task_detail', args=[project_id, user_story_id, id])
            task.user_story = story
            task.is_blocked = False
            task.taglist = parse_tag_input(tags)
            story.tasks.append(task)
            result.hours += estimate or 0

            if not task_owner.has_key(username):
                if first_name and last_name:
                    task_owner[username] = '%s %s' % (first_name, last_name)
                elif first_name:
                    task_owner [username]= first_name
                elif last_name:
                    task_owner[username] = last_name
                elif email:
                    task_owner[username] = email
                else:
                    task_owner[username] = username
            task.owner = task_owner[username]

            if task.owner:
                result.tags[task.owner].append(task)
            else:
                result.tags['unassigned'].append(task)

            for tag in task.taglist:
                result.tags[tag].append(task)

            task.remaining_for_day = [None for day in activedays]
            task.remaining_for_day[0] = estimate or 0
            task.remaining_for_day[today] = remaining or 0
            tasks_by_id[id] = task

        ## tasklog updates
        cursor.execute("""select tl.old_remaining, tl.date, tl.time_on_task, t.id
                          from agilito_tasklog tl
                          join agilito_task t on tl.task_id = t.id
                          join agilito_userstory s on t.user_story_id = s.id
                          where s.iteration_id = %s and tl.date<=%s
                          order by tl.date
                          """, (self.id, datetime.date.today()))
        for old_remaining, date, spent, task in cursor.fetchall():
            try:
                tasks_by_id[task].remaining_for_day[tasklogday(date)] = old_remaining
            except KeyError:
                continue

            if spent:
                result.time_spent += spent

        ## fill out burndown by overwriting None values with the earliest updated value
        revdays = list(reversed(activedays))
        for id, task in tasks_by_id.items():
            for day in revdays:
                if task.remaining_for_day[day] is None:
                    task.remaining_for_day[day] = task.remaining_for_day[day+1]

        ## now that we have all task data we can update the story stats for all days spent in the iteration
        for story in result.stories:
            size = story.size or 0
            for day in activedays:
                hours = sum(task.remaining_for_day[day] for task in story.tasks)
                if hours == 0:
                    points = 0
                else:
                    points = size
                story.tmp.hours_remaining_for_day[day] = hours
                story.tmp.points_remaining_for_day[day] = points
            story.estimate = story.tmp.hours_remaining_for_day[0]
            story.remaining = story.tmp.hours_remaining_for_day[-1]

        result.burndown._('remaining').hours = [sum(story.tmp.hours_remaining_for_day[day] for story in result.stories) for day in activedays]
        result.burndown.remaining.points = [sum(story.tmp.points_remaining_for_day[day] for story in result.stories) for day in activedays]

        result.burndown._('max').hours = max(result.burndown.remaining.hours)
        result.burndown.max.points = max(result.burndown.remaining.points)

        result._('velocity').planned = result.burndown.remaining.points[0]
        result.velocity.actual = result.velocity.planned - result.burndown.remaining.points[-1]

        ## data points for the ideal
        ideal = [0.0] * result.burndown.days
        delta = result.burndown.days - 1
        deltainv = 1.0 / delta
        maxh = result.burndown.remaining.hours[0]
        for day in dayrange:
            ideal[day] = deltainv * maxh * day
        result.burndown.remaining.ideal = list(reversed(ideal))

        left = result.burndown.remaining.ideal[today]
        unsized = False
        for us in result.stories:
            unsized = (us.size is None or unsized)
            if not us.remaining is None and left >= us.remaining:
                us.is_starved = False
                left -= us.remaining
            else:
                us.is_starved = True
        result.burndown.unsized_stories = unsized

        ## impediments
        impediment = {}
        result._('impediments').resolved = []
        result.impediments.open = []
        cursor.execute("""select i.id, i.name, i.resolved, t.id
                          from agilito_impediment i
                          join agilito_impediment_tasks it on it.impediment_id = i.id
                          join agilito_task t on it.task_id = t.id
                          join agilito_userstory s on t.user_story_id = s.id
                          where s.iteration_id = %s
                          """, (self.id,))
        for id, name, resolved, taskid in cursor.fetchall():
            try:
                task = tasks_by_id[taskid]
            except KeyError:
                continue

            try:
                imp = impediment[id]
            except KeyError:
                imp = Object(id=id, name=name, resolved=resolved, risk=0)
                imp.tasks = []
                imp.get_absolute_url = reverse('agilito.views.impediment_edit', args=[project_id, self.id, id])
                imp._('tmp').storysize = {}

                impediment[id] = imp

                if resolved:
                    result.impediments.resolved.append(imp)
                else:
                    result.impediments.open.append(imp)

            imp.tasks.append(task)
            task.is_blocked = not resolved
            story = task.user_story
            if task.is_blocked:
                story.is_blocked = True

            if story.remaining > 0:
                imp.tmp.storysize[story.id] = story.size or 0

        if len(result.impediments.resolved) == 0:
            result.impediments.resolved = None
        if len(result.impediments.open) == 0:
            result.impediments.open = None

        if result.size and not result.impediments.open is None:
            factor = float(result.size) / 100
            for imp in result.impediments.open:
                imp.risk = sum(imp.tmp.storysize.values()) / factor

        result.remaining = result.burndown.remaining.hours[-1]
        return result.clean()

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
        ordering = ('start_date',)

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
                (10, 'Defined'),
                (15, 'Specified'),
                (20, 'In Progress'),
                (30, 'Completed'),
                (40, 'Accepted'),
                (50, 'Failed'),
                )
    ENDSTATES = (STATES.ACCEPTED, STATES.FAILED)

    SIZES = FieldChoices(
                (1,  'XXS'),
                (2,  'XS'),
                (3,  'S'),
                (5,  'M'),
                (8,  'L'),
                (13, 'XL'),
                (21, 'XXL'),
                (1000,  'Infinity'))

    project = models.ForeignKey(Project)

    iteration = models.ForeignKey(Iteration, null=True, blank=True)
    rank = models.IntegerField(null=True, blank=True)

    state = models.SmallIntegerField(choices=STATES.choices(), default=STATES.DEFINED)

    if UNRESTRICTED_SIZE:
        size = models.SmallIntegerField(null=True, blank=True)
    else:
        size = models.SmallIntegerField(choices=SIZES.choices(), null=True)

    created = models.DateField(default=datetime.datetime.now)
    closed = models.DateField(null=True)

    tags = TagField()

    copied_from = models.ForeignKey('UserStory', null=True)

    @property
    def taglist(self):
        return parse_tag_input(self.tags)

    def __unicode__(self):
        return u'US%s: %s' % (self.id, self.name)

    @staticmethod
    def size_label_for(size):
        if not size:
            return '?'
        if UNRESTRICTED_SIZE:
            return str(size)

        return UserStory.SIZES.label(size)

    @property
    def size_label(self):
        return UserStory.size_label_for(self.size)

    @property
    def state_label(self):
        return UserStory.STATES.label(self.state)

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
        return sum(t.estimate for t in self.task_set.all() if t.estimate)

    @property
    def actuals(self):
        return sum(t.actuals for t in self.task_set.all() if t.actuals)

    @property
    def remaining(self):
        return sum(t.remaining for t in self.task_set.all() if t.remaining)

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

    def copy_to_iteration(self, iteration, copy_tasks, state):
        id = self.id

        tasks = self.task_set.all()

        self.id = None
        self.iteration=iteration
        self.state = UserStory.STATES.DEFINED
        self.created = datetime.datetime.now()
        self.copied_from = UserStory.objects.get(id=id)
        #self.generation = self.copied_from.generation + 1
        self.save()

        if copy_tasks:
            for task in tasks:
                task.id = None
                task.user_story = self
                task.estimate = task.remaining
                task.state = Task.STATES.DEFINED
                task.save()

        if state == UserStory.STATES.FAILED:
            story = UserStory.objects.get(id=id)
            story.state = state
            story.save()

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
        if self.state in UserStory.ENDSTATES:
            if self.closed is None:
                self.closed = datetime.date.today()
        else:
            self.closed = None

        super(UserStory, self).save()

        if self.rank:
            self.project.reorder_backlog('userstory', self.id, self.rank)

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

    estimate = models.FloatField(blank=True, null=True)
    remaining = models.FloatField(blank=True, null=True)

    state = models.SmallIntegerField(choices=STATES.choices(), default=STATES.DEFINED)

    category = models.SmallIntegerField(choices=CATEGORIES.choices(), default=CATEGORIES.UNDEFINED)

    owner = models.ForeignKey(User, blank=True, null=True)
    user_story = models.ForeignKey('UserStory')

    # alter table agilito_task add column tags varchar(255) NOT NULL default ''
    tags = TagField()

    @property
    def project(self):
        return self.user_story.project

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
    def is_in_progress(self):
        return (self.state == Task.STATES.IN_PROGRESS)

    @property
    def is_defined(self):
        return (self.state == Task.STATES.DEFINED)

    def __unicode__(self):
        return u'TA%s: %s' % (self.id, self.name)

    def get_container_model(self):
        return self.user_story

    def save(self, tasklog=None, user=None):
        if not self.id is None:
            old = Task.objects.get(id=self.id)
            if (old.remaining != self.remaining) or tasklog:
                if tasklog is None:
                    tasklog = TaskLog()
                    tasklog.owner = user

                if tasklog.time_on_task is None:
                    if old.remaining is None or self.remaining is None:
                        tasklog.time_on_task = 0
                    else:
                        tasklog.time_on_task = old.remaining - self.remaining
                if tasklog.time_on_task < 0:
                    tasklog.time_on_task = 0

                tasklog.task = self
                tasklog.summary = (tasklog.summary or 'update')
                tasklog.date = (tasklog.date or datetime.datetime.now())
                tasklog.iteration = self.user_story.iteration
                tasklog.old_remaining = old.remaining
                tasklog.save()

        super(Task, self).save()

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
    opened = models.DateField(default=datetime.datetime.now)
    resolved = models.DateTimeField(null=True)

    tasks = models.ManyToManyField('Task')

    @models.permalink
    def get_absolute_url(self):
        it = self.tasks.all()[0].user_story.iteration

        return PERMLINK_PREFIX + 'impediment_edit', (), {'project_id': it.project.id, 'iteration_id': it.id, 'impediment_id': self.id }

    @property
    def project(self):
        return self.tasks.all()[0].user_story.project

    class Meta:
        ordering = ('-opened',)        
        
        verbose_name = _(u'Impediment')
        verbose_name_plural = _(u'Impediments')

        permissions = (
            ('view', 'Can view the impediments.'),
        )

class TaskLog(models.Model):
    task = models.ForeignKey('Task')
    time_on_task = models.FloatField()
    summary = models.TextField()
    date = models.DateTimeField()
    iteration = models.ForeignKey('Iteration', null=True)
    owner = models.ForeignKey(User)
    old_remaining = models.FloatField()

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

class ArchivedBacklog(models.Model):
    stamp = models.DateTimeField()
    project = models.ForeignKey(Project)
    commit = models.TextField()

    class Meta:
        ordering = ('-stamp',)
