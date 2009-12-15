#!/usr/bin/env python

import os, sys, codecs, datetime, re
import subprocess

# prep for django
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
projectdir = os.path.abspath(os.path.dirname(__file__))
while projectdir != '/' and not os.path.exists(os.path.join(projectdir, 'settings.py')):
    projectdir = os.path.dirname(projectdir)
if projectdir != '/':
    sys.path.append(projectdir)

from agilito.reporting import HTML, Calc

def call(cmd):
    p = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, close_fds=True)
    output = p.stdout.read()
    p.wait()
    return output

def render(d, data):
    doc = Calc(sheetname=data['title'])

    for col, h in enumerate(['Rank', 'Id', 'Name', 'Description', 'Size', 'State', 'Tags']):
        doc.write((0, col), h, {'bold': True})

    row = 0
    for story in data['backlog']:
        if story.whatami != 'UserStory':
            continue

        row += 1
        doc.write((row, 0), story.rank)
        doc.write((row, 1), story.id)
        doc.write((row, 2), story.name)
        doc.write((row, 3), HTML(story.description))

        if data['sizes']:
            doc.write((row, 4), UserStory.SIZES.label(story.size))
        else:
            doc.write((row, 4), story.size)

        doc.write((row, 5), story.backlog_state)
        doc.write((row, 6), ', '.join(story.taglist))

    doc.save(d)

from agilito.models import Project, UserStory
from agilito import BACKLOG_ARCHIVE, UNRESTRICTED_SIZE
from django.template import loader

if not BACKLOG_ARCHIVE:
    print 'Backlog archival not configured'
    sys.exit(1)

if not os.path.exists(BACKLOG_ARCHIVE):
    print 'Backlog archival path does not exist'
    sys.exit(1)

if not os.path.exists(os.path.join(BACKLOG_ARCHIVE, '.git')):
    print 'Backlog archival path is not a git repository'
    sys.exit(1)

from dulwich.repo import Repo

sizes = not UNRESTRICTED_SIZE
for project in Project.objects.all():
    data =  {'title': project.name,
             'backlog': project.backlog(UserStory.STATES.values()).backlog,
             'sizes': sizes,
            }
    render(os.path.join(BACKLOG_ARCHIVE, '%d.ods' % project.id), data)

os.chdir(BACKLOG_ARCHIVE)

call('git add .')
call('git commit -a -m "%s"' % datetime.date.today().isoformat())

from django.db import connection, transaction
cursor = connection.cursor()

cursor.execute('delete from agilito_archivedbacklog')
id = 0

projects = []
repo = Repo(BACKLOG_ARCHIVE)
for commit in repo.revision_history(repo.head()):
    for mode, name, sha in repo.tree(commit.tree).entries():
        m = re.match('([0-9]+)[.]ods$', name)
        if not m:
            continue

        project_id = int(m.group(1))
        if not project_id in projects:
            projects.append(project_id)

        id += 1
        cursor.execute("""  insert into agilito_archivedbacklog (id, stamp, project_id, commit)
                            values (%s, %s, %s, %s)""", (id, datetime.datetime.fromtimestamp(commit.commit_time), project_id, commit.tree))

transaction.commit_unless_managed()
for project_id in projects:
    Project.touch_cache(project_id)
