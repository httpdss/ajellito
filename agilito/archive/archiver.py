#!/usr/bin/env python

import os, sys, codecs, datetime, re
import subprocess

os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

def call(cmd):
    p = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, close_fds=True)
    output = p.stdout.read()
    p.wait()
    return output

# find project directory and add it to the path
projectdir = os.path.abspath(os.path.dirname(__file__))
while projectdir != '/' and not os.path.exists(os.path.join(projectdir, 'settings.py')):
    projectdir = os.path.dirname(projectdir)
if projectdir != '/':
    sys.path.append(projectdir)

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
    archive = codecs.open(os.path.join(BACKLOG_ARCHIVE, '%d.html' % project.id), 'w', 'utf-8')
    archive.write(loader.render_to_string('product_backlog_archive.html', data))
    archive.close()

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
        m = re.match('([0-9]+)[.]html$', name)
        if not m:
            continue

        #print GitObjectStore.tree_lookup_path(repo.object_store.__getitem__, commit.tree, name)

        project_id = int(m.group(1))
        if not project_id in projects:
            projects.append(project_id)

        id += 1
        cursor.execute("""  insert into agilito_archivedbacklog (id, stamp, project_id, commit)
                            values (%s, %s, %s, %s)""", (id, datetime.datetime.fromtimestamp(commit.commit_time), project_id, commit.tree))

transaction.commit_unless_managed()
for project_id in projects:
    Project.touch_cache(project_id)
