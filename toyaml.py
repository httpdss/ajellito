#!/usr/bin/python
import agilito.tests
from settings import TIME_ZONE
import time
import yaml
import codecs
import types
from StringIO import StringIO
import sys
import os

SAMPLE = False

from agilito.models import Project, UserStory, Iteration, Task, Impediment
from threadedcomments.models import ThreadedComment
from django.contrib.auth.models import User

import datetime

from html2textile import totextile

if os.path.exists('key_users.yaml'):
    f = open('key_users.yaml')
    KEY_USERS = yaml.load(f.read())
    f.close()
else:
    raise Exception('you must specify the key users per project')

DEFAULT_USER = None

def tostr(s):
    try:
        return str(s)
    except UnicodeEncodeError:
        return s

def validData(s):
    if s == []: return False
    if isinstance(s, types.StringTypes) and not s: return False
    if s is None: return False
    return True

def journal(date, user, prop, old, nw):
    j = {}
    j['timestamp'] = date
    if user is None:
        j['username'] = DEFAULT_USER
    else:
        j['username'] = user.username
    j['activity'] = {prop: {'old': old, 'new': nw}}
    return j

def normalize(x):
    if isinstance(x, types.DictType):
        for k in x.keys():
            if validData(x[k]):
                x[k] = normalize(x[k])
            else:
                del x[k]

    elif isinstance(x, types.StringTypes):
        x = tostr(x.strip())

    elif isinstance(x, (types.ListType, types.TupleType)):
        x = [normalize(m) for m in x if validData(m)]

    elif x.__class__.__name__ == 'datetime':
        return x.date()

    return x

ISSUES = {}
def issue_key(prefix, id):
    key = '%s_%d' % (prefix, id)
    if not ISSUES.has_key(key): ISSUES[key] = 'issue_%d' % len(ISSUES.keys())
    return ISSUES[key]

def story_key(id):
    return issue_key('story', id)

def task_key(id):
    return issue_key('task', id)

def sprint_key(id):
    return 'sprint_%d' % id

def impediment_key(id):
    return issue_key('impediment', id)

def dump_story(s,issues):
    dump = {}
    issues[story_key(s.id)] = dump

    dump['name'] = '%s (#%d)' % (s.name, s.id)
    dump['type'] = 'Story'
    dump['author'] = DEFAULT_USER
    dump['description'] = totextile(s.description)
    dump['status'] = UserStory.STATES.label(s.state)
    dump['points'] = s.size
    dump['position'] = s.rank
    dump['created'] = s.created
    if s.iteration: dump['sprint'] = sprint_key(s.iteration.id)
    if not s.closed is None:
        dump['history'] = [journal(s.closed, None, 'status', UserStory.STATES.label(UserStory.STATES.SPECIFIED), dump['status'])]
    if not s.tags is None: dump['tags'] = s.taglist

    if s.state in UserStory.ENDSTATES:
        dump['done'] = 100
    else:
        dump['done'] = 0

def time_entry_object(task, tasklog):
    te = {}
    te['timestamp'] = tasklog.date
    te['username'] = tasklog.owner.username
    te['issue'] = task_key(task.id)
    te['hours'] = tasklog.time_on_task
    te['comments'] = totextile(tasklog.summary)
    te['activity'] = Task.CATEGORIES.label(task.category)
    return te

def dump_task(t, issues, time_entries):
    task = {}
    issues[task_key(t.id)] = task

    task['name'] = t.name
    task['type'] = 'Task'

    if t.owner is None:
        task['author'] = DEFAULT_USER
    else:
        task['author'] = t.owner.username
        task['assigned'] = t.owner.username

    task['description'] = totextile(t.description)
    task['status'] = Task.STATES.label(t.state)
    task['estimate'] = t.estimate
    task['remaining'] = t.remaining
    task['category'] = Task.CATEGORIES.label(t.category)
    task['parent'] = story_key(t.user_story.id)
    if not t.tags is None: task['tags'] = t.taglist
    if t.user_story.iteration: task['sprint'] = sprint_key(t.user_story.iteration.id)
    task['history'] = []

    value = t.remaining
    for tl in t.tasklog_set.all():
        if tl.old_remaining is None: tl.old_remaining = t.estimate
        if tl.old_remaining != value:
            j = journal(tl.date, tl.owner, 'remaining_hours', tl.old_remaining, value)
            value = tl.old_remaining
            task['history'].append(j)

        if not tl.owner is None and not tl.time_on_task is None and tl.time_on_task != 0:
            time_entries.append(time_entry_object(t, tl))

def dump_impediment(i, issues):
    imp = {}
    issues[impediment_key(i.id)] = imp

    imp['name'] = impediment.name
    imp['author'] = DEFAULT_USER
    imp['type'] = 'Impediment'
    imp['description'] = totextile(impediment.description)
    imp['created'] = impediment.opened

    if impediment.resolved is None:
        imp['status'] = 'open'
    else:
        imp['status'] = 'closed'
        imp['history'] = [journal(impediment.resolved, None, 'status', 'open', 'closed')]

    imp['blocks'] = []
    for t in Task.objects.filter(impediment=i).distinct():
        imp['blocks'].append(task_key(t.id))
        if t.user_story.iteration: imp['sprint'] = sprint_key(t.user_story.iteration.id)


for project in Project.objects.all():
    print 'Generating %s...' % project.name
    pname = project.name
    if SAMPLE: pname = 'Sample'
    pdump = {'name': pname, 'sprints': {}, 'members': {}, 'description': totextile(project.description)}

    DEFAULT_USER = None
    if KEY_USERS.has_key(project.name): DEFAULT_USER = KEY_USERS[project.name]

    for user in project.project_members.all():
        pdump['members'][tostr(user.username)] = {
            'email': user.email,
            'lastname': user.last_name,
            'firstname': user.first_name,
            'active': user.is_active,
            'admin': user.is_superuser or user.is_staff,
            'role': 'member'
        }

    if not DEFAULT_USER in pdump['members'].keys():
        raise Exception("Project %s: members: %s" % (project.name, ', '.join(pdump['members'].keys())))

    for sprint in project.iteration_set.all():
        sprint_id = sprint_key(sprint.id)
        pdump['sprints'][sprint_id] = {'name': sprint.name, 'description': totextile(sprint.description), 'start': sprint.start_date, 'end': sprint.end_date}
        current_sprint = pdump['sprints'][sprint_id]
        current_sprint['open'] = sprint.start_date is None or sprint.end_date is None or (sprint.start_date >= datetime.date.today() and datetime.date.today() <= sprint.end_date)

        wikipage = ''
        for comment in ThreadedComment.objects.filter(object_id = sprint.id):
            wikipage += 'h1. %s (%s)\n' % (comment.user, comment.date_submitted)
            wikipage += '%s\n' % comment.comment

        current_sprint['wiki'] = wikipage

        burndown = sprint.status().burndown
        points_committed = burndown.remaining.points[0]
        current_sprint['burndown'] = [{
                'date': burndown.dates[i],
                'remaining_hours': burndown.remaining.hours[i],
                'points_resolved': (points_committed - burndown.remaining.points[i]),
                'points_committed': points_committed}
            for i in range(len(burndown.remaining.hours))]

    pdump['issues'] = {}
    for story in project.userstory_set.all():
        dump_story(story, pdump['issues'])

    pdump['time_entries'] = []
    for task in Task.objects.filter(user_story__project = project).distinct():
        dump_task(task, pdump['issues'], pdump['time_entries'])

    for impediment in Impediment.objects.filter(tasks__user_story__project = project).distinct():
        dump_impediment(impediment, pdump['issues'])

    if SAMPLE:
        f = codecs.open('%s.sample.yaml' % project.name, 'w', 'utf-8')
    else:
        f = codecs.open('%s.yaml' % project.name, 'w', 'utf-8')
    f.write(yaml.dump(normalize(pdump), encoding='utf-8'))
    f.close()
