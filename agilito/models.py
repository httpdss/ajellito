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

from dateutil.rrule import rrule, DAILY, MO, TU, WE, TH, FR
import datetime, time
import math, re

from agilito import CACHE_ENABLED, UNRESTRICTED_SIZE, CACHE_PREFIX

def rounded(v, p):
    return Decimal(v).quantize(Decimal('1.' + ('0' * p)))

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

    @cached
    def velocity(self):
        vs = filter(lambda x: not x is None, [it.velocity() for it in self.iteration_set.all()])

        sprints = len(vs)
        if sprints == 0:
            return {'actual':None, 'estimated':None, 'sprint_length':None}

        pv = {}
        for key in ['actual', 'estimated', 'sprint_length']:
            pv[key] = float(sum(v[key] for v in vs if not v[key] is None)) / sprints
        return pv

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
        cache.set('project-cache-version-%s' % id, v, delta.seconds)
        return v

    @classmethod
    def cache_id(klass, id):
        v = cache.get('project-cache-version-%s' % id)
        if not v:
            return Project.touch_cache(id)
        return v

    @cached
    def backlog(self, states):
        stories = list(UserStory.objects.reset().filter(project=self, state__in=states))
        releases = list(Release.objects.filter(project=self))

        suggested_size = self.suggest_sizes()
        for us in stories:
            if suggested_size.has_key(us.id):
                us.suggested_size = suggested_size[us.id]
            else:
                us.suggested_size = None

        pbl = []
        norank = []
        while stories and releases:
            if stories[0].rank is None:
                norank.append(stories.pop(0))
            elif stories[0].rank < releases[0].rank:
                pbl.append(stories.pop(0))
            elif pbl == []: # don't start the PBL with an empty release
                releases.pop(0) 
            else:
                pbl.append(releases.pop(0))

        pbl.extend(releases)
        pbl.extend(stories)
        pbl.extend(norank)
        return pbl

    def closest(self, v, choices):
        sel = 0
        d = None

        for i, c in enumerate(choices):
            if d is None or math.fabs(v - c) < d:
                sel = i
                d = math.fabs(v - c)
        return sel

    def baseline_story(self, stories):
        data = []
        for story in stories:
            hours = story.actuals or story.estimated
            if not hours:
                continue

            data.append((story.id, float(hours)))

        if len(data) == 0:
            return None

        avg = sum(d[1] for d in data)/len(data)

        baseline = self.closest(avg, [d[1] for d in data])
        return UserStory.objects.get(id=data[baseline][0])

    @cached
    def suggest_sizes(self, baseline=None, size=5, only_sized=False, include_original=False): # UserStory.SIZES.M): but needs forward declaration
        if only_sized and not UNRESTRICTED_SIZE:
            stories = self.userstory_set.exclude(size=None).exclude(size=UserStory.SIZES.INFINITY)
        else:
            stories = list(self.userstory_set.exclude(size=None).all())

        if baseline is None:
            baseline = self.baseline_story(stories)

        if baseline is None:
            return {}

        factor = float(size) / float(baseline.actuals or baseline.estimated)

        if UNRESTRICTED_SIZE:
            sizes = list(set(s.size for s in stories if s.size))
        else:
            sizes = [s for s in UserStory.SIZES.values() if s != UserStory.SIZES.INFINITY]
        
        suggestions = {}
        for story in stories:
            hours = float(story.actuals or story.estimated)
            if not hours:
                continue

            suggestions[story.id] = sizes[self.closest(int(factor * hours), sizes)]
            if include_original:
                suggestions[story.id] = (suggestions[story.id], story.size)

        return suggestions

    @cached
    def size_estimation_accuracy(self):
        sugg = self.suggest_sizes(only_sized = True, include_original = True).values()

        try:
            return (float(sum(s[0] for s in sugg)) / sum(s[1] for s in sugg)) * 100
        except ZeroDivisionError:
            return None

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
                if r: ranks.append(r)

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

def toprank():
    from django.db import connection, transaction
    c = connection.cursor()
    c.execute("""select coalesce(max(rank), 0) + 1 as rank from agilito_userstory
                 union
                 select coalesce(max(rank), 0) + 1 from agilito_release
                 order by rank desc""")
    return c.fetchone()[0]

class Release(ClueModel):
    project = models.ForeignKey(Project)
    rank = models.IntegerField(default=toprank)
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

    @cached
    def release_date(self):
        from django.db import connection, transaction
        c = connection.cursor()

        status = {
            'date': None,
            'achieved': False,
            'error': None,
            'severity': None
        }

        end_states = ','.join(str(s) for s in UserStory.ENDSTATES)

        # unsized
        c.execute("""
            select count(*)
            from agilito_userstory
            where project_id = %%s
            and iteration_id is NULL
            and size is NULL
            and not state in (%s)
            and rank < %%s""" % end_states, (self.project.id, self.rank))
        unsized = c.fetchone()[0]

        if unsized > 0:
            status['error'] = 'release has unsized stories'
            status['severity'] = 'error'
            return status

        # unplanned
        c.execute("""
            select sum(size)
            from agilito_userstory
            where project_id = %%s
            and iteration_id is NULL
            and not size is NULL
            and not state in (%s)
            and rank < %%s""" % end_states, (self.project.id, self.rank))
        unplanned = c.fetchone()[0]
        if unplanned is None:
            unplanned = 0

        pv = self.project.velocity()
        pva = float(pv['actual']) / pv['sprint_length']
        pve = float(pv['estimated']) / pv['sprint_length']

        if unplanned > 0 and (pv['actual'] is None or pv['actual'] == 0):
            status['error'] = 'project has unknown velocity'
            status['severity'] = 'error'
            return status
        else:
            # correct for weekdays
            unplanned = unplanned * pva * (7.0/5)

        # planned but unfinished
        c.execute("""
            select max(i.end_date), max(us.id)
            from agilito_userstory us
            left join agilito_iteration i on us.iteration_id = i.id and not state in (%s) and us.rank < %%s
            where us.project_id = %%s""" % end_states, (self.project.id, self.rank))
        sprints_end, unfinished = c.fetchone()[0]
        if sprints_end is None: # no sprints defined
            sprints_end = datetime.date.today()
        elif not unfinished is None and pve > 1.1 * pva and sprints_end > datetime.date.today():
            status['error'] = 'sprints based on unproven velocity'
            status['severity'] = 'warning'
        else:
            status['achieved'] = unfinished is None

        rd = sprints_end + datetime.timedelta(unplanned)
        status['date'] = rd
        if self.deadline and rd > self.deadline:
            status['error'] = 'deadline exceeded'
            status['severity'] = 'error'
            return status

        return status

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
                                                
    @property
    def us_accepted(self):
        return sum(us.size or 0 for us in self.userstory_set.filter(Q(state=UserStory.STATES.ACCEPTED)))
    
    @property
    def us_accepted_percentage(self):
        total = sum(us.size or 0 for us in self.userstory_set.all())
        accepted = self.us_accepted
        if total <> 0:
            return (float(accepted)/float(total))*100 
        else:
            return 0

    @cached
    def velocity(self):
        d = self.total_days()
        if d == 0:
            return None

        s = [(us.size or 0, us.state==UserStory.STATES.ACCEPTED) for us in self.userstory_set.all()]

        v = {}
        v['estimated'] = sum(e[0] for e in s)
        if v['estimated'] == 0:
            return None

        v['sprint_length'] = d

        if self.end_date > datetime.date.today():
            v['actual'] = None
        else:
            v['actual'] = sum(a[0] for a in filter(lambda x: x[1], s))

        return v

    @cached
    def day_number(self, date):
        """
        Return the day of the iteration we're on.
        date is start-of-day.
        """
        until = min(self.end_date + datetime.timedelta(1), date) - datetime.timedelta(1)
        return rrule(DAILY, cache=True,
                     dtstart=self.start_date, until=until,
                     byweekday=(MO,TU,WE,TH,FR)).count()

    @cached
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
        return rounded(estimated - estimated * elapsed / ndays, 2)

    def remaining_hours(self, date):
        return sum(t.remaining_for_date(date) for t in Task.objects.filter(user_story__iteration=self))

    def remaining_storypoints(self, date):
        is_start = same_date(date, self.start_date)
        return sum(us.size or 0 for us in self.userstory_set.all() if is_start or us.remaining_for_date(date) > 0)

    def total_estimated(self):
        return sum(t.estimate or 0
                   for t in Task.objects.filter(user_story__iteration=self))

    def user_estimated(self, userid):    
        tasks = Task.objects.filter(owner__id=userid, user_story__iteration__pk=self.id)

        return sum(t.estimate or 0 for t in tasks)

    def user_progress(self, userid):
        tasklogs = self.tasklog_set.filter(owner__id=userid)
        return sum(tl.time_on_task or 0 for tl in tasklogs)

    @cached
    def burndown_data(self):
        burndown = []
        today = datetime.date.today()
        rr = list(rrule(DAILY, cache=True,
                        dtstart=self.start_date, until=self.end_date,
                        byweekday=(MO,TU,WE,TH,FR)))
        rr.append(rr[-1] + datetime.timedelta(1))
        for i, a_datetime in enumerate(rr):
            a_date = a_datetime.date()
            data = dict(day=i, ideal=self.ideal_hours(a_date))
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
            card['StorySize'] = us.size_label
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

            if not t.owner:
                owner = 'Unassigned'
            elif t.owner.first_name or t.owner.last_name:
                owner = ' '.join([n for n in [t.owner.first_name, t.owner.last_name] if n])
            elif t.owner.email:
                owner = t.owner.email
            else:
                owner = t.owner.username
            card['TaskOwner'] = owner

            card['TaskTags'] = t.tags.replace('"', '')

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

class UserStoryManager(models.Manager):
    def get_query_set(self):
        return super(UserStoryManager, self).get_query_set().filter(state__in=UserStory.STATES.keys)

    def reset(self):
        return super(UserStoryManager, self).get_query_set()

    def get(self, *args, **kwargs):
        return self.reset().get(*args, **kwargs)

class UserStory(ClueModel):
    STATES = FieldChoices(
                (10, 'Defined'),
                (15, 'Specified'),
                (20, 'In Progress'),
                (30, 'Completed'),
                (40, 'Accepted'),
                (50, 'Failed'),
                (1, '#Archived')
                )
    ENDSTATES = (STATES.ACCEPTED, STATES.FAILED, STATES.ARCHIVED)

    SIZES = FieldChoices(
                (1,  'XXS'),
                (2,  'XS'),
                (3,  'S'),
                (5,  'M'),
                (8,  'L'),
                (13, 'XL'),
                (21, 'XXL'),
                (1000,  'Infinity'))

    objects = UserStoryManager()

    project = models.ForeignKey(Project)

    iteration = models.ForeignKey(Iteration, null=True, blank=True)
    rank = models.IntegerField(null=True, blank=True)

    state = models.SmallIntegerField(choices=STATES.choices(), default=STATES.DEFINED)

    if UNRESTRICTED_SIZE:
        size = models.SmallIntegerField(null=True, blank=True)
    else:
        size = models.SmallIntegerField(choices=SIZES.choices(), null=True)

    # alter table agilito_userstory add column created date NOT NULL default 'now',
    # alter table agilito_userstory add column closed date
    created = models.DateField(default=datetime.datetime.now)
    closed = models.DateField(null=True)

    # alter table agilito_userstory add column tags varchar(255) NOT NULL default ''
    tags = TagField()

    copied_from = models.ForeignKey('UserStory', null=True)
    #generation = models.SmallIntegerField(default=1)

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
    def backlog_state(self):
        if self.state == UserStory.STATES.ARCHIVED:
            return 'archived'

        if self.state == UserStory.STATES.ACCEPTED:
            return 'accepted'

        if self.state == UserStory.STATES.FAILED:
            return 'failed'

        if self.state == UserStory.STATES.DEFINED and self.iteration is None:
            return 'needs-work'

        if self.iteration is None:
            return 'unplanned'

        if self.iteration.start_date > datetime.date.today():
            return 'planned'

        if self.iteration.end_date < datetime.date.today():
            return 'forgotten'

        # allow for one day of leeway
        if self.iteration.end_date >= (datetime.date.today() - datetime.timedelta(days=1)): 
            return 'in-progress'

        return 'unknown'

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

    def remaining_for_date(self, date):
        return sum(t.remaining_for_date(date) for t in self.task_set.all())

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

    def copy_to_iteration(self, iteration, copy_tasks, state, archiver):
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

        elif state == UserStory.STATES.ARCHIVED:
            story = UserStory.objects.get(id=id)
            story.archive(archiver)

    def archive(self, archiver):
        for task in self.task_set.all():
            task.archive(archiver)

        self.state = UserStory.STATES.ARCHIVED
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

class TaskManager(models.Manager):
    def get_query_set(self):
        return super(TaskManager, self).get_query_set().filter(state__in=Task.STATES.keys)

    def reset(self):
        return super(TaskManager, self).get_query_set()

    def get(self, *args, **kwargs):
        return self.reset().get(*args, **kwargs)

class Task(ClueModel):
    STATES = FieldChoices(
                (1, '#Archived'),
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

    objects = TaskManager()

    estimate = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    remaining = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)

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
    def is_archived(self):
        return (self.state == Task.STATES.ARCHIVED)

    @property
    def is_in_progress(self):
        return (self.state == Task.STATES.IN_PROGRESS)

    @property
    def is_defined(self):
        return (self.state == Task.STATES.DEFINED)

    def archive(self, archiver):
        self.state = Task.STATES.ARCHIVED
        self.save(user=archiver)

    def remaining_for_date(self, date):
        # for edits past the sprint end
        if same_date(date, datetime.date.today()) or date > self.user_story.iteration.end_date:
            return self.remaining or 0

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

    def save(self, tasklog=None, user=None):
        if self.state == Task.STATES.ARCHIVED:
            self.remaining = 0

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
