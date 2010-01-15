#!/usr/bin/env python

import sys, os, shutil, re
from distutils.sysconfig import get_python_lib
import tempfile
import uuid
import getopt
import urllib, urllib2
import subprocess

def call(cmd):
    p = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, close_fds=True)
    output = p.stdout.read()
    p.wait()
    return output

try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["install=", "verbose", "apache", "nosqldiff", 'debug'])
except getopt.GetoptError, err:
    print str(err)
    sys.exit(1)

config = {'verbose': False, 'install': 'ask', 'apache': False, 'nosqldiff': False, 'debug': False}
for o, a in opts:
    if o == '--install':
        if not a in ['auto', 'ask']:
            print 'Unknown install option "%s"' % a
            sys.exit(1)
        config['install'] = a

    elif o == '--apache':
        config['apache'] = True

    elif o == '--nosqldiff':
        config['nosqldiff'] = True

    elif o == '--verbose':
        config['verbose'] = True

    elif o == '--debug':
        config['debug'] = True

    else:
        assert False, 'Unknown option "%s"' % o

#tmpdir = tempfile.mkdtemp()
TMPDIR = '/tmp/django'
shutil.rmtree(TMPDIR, True)

os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

installdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def fullPath(*args):
    global installdir

    path = installdir[:]
    for p in args:
        path = os.path.join(path, p)
    return path

if not os.path.exists(fullPath('settings.py')):
    f = open(fullPath('agilito', 'install', 'settings_template.py'))
    body = f.read()
    f.close()
    f = open(fullPath('settings.py'), 'w')
    secret = (str(uuid.uuid4()) + str(uuid.uuid4())).replace("'", 'x')
    f.write(body % {'secret': secret })
    f.close()

sys.path.append(installdir)
os.chdir(installdir)

class Module:
    available = []
    required = []
    apps = []

    OK = True

    def __init__(self, name, **kwargs):
        self.name = name
        self.optional = False
        self.app = True
        self.url = None
        self.subdir = None
        self.branch = None
        self.app = True

        for k, v in kwargs.items():
            setattr(self, k, v)

    def askDownload(self):
        return True

    def download(self):
        print '%s is available at %s' % (self.name, self.url)

    def markPresent(self):
        global config

        if config['verbose']:
            print '** %s is present' % self.name
        if self.app:
            Module.apps.append(self.name)
        Module.available.append(self.name)

    def verify(self, retry=True):
        if not self.optional:
            Module.required.append(self.name)

        present = False
        try:
            __import__(self.name)
            present = True
        except ImportError, e:
            if str(e).find('DJANGO_SETTINGS_MODULE') >= 0:
                present = True

        if present:
            self.markPresent()
            return True

        if self.optional:
            print '\nIf you install %s you will get additional features in Agilito' % self.name
        else:
            print '\nYou need to have %s installed' % self.name


        do_download = False
        do_download = do_download or (config['install'] == 'ask' and self.askDownload())
        do_download = do_download or config['install'] == 'auto'
        if not do_download:
            Module.OK = Module.OK and self.optional
            return self.optional

        self.download()

        try:
            __import__(self.name)
            present = True
        except ImportError, e:
            if str(e).find('DJANGO_SETTINGS_MODULE') >= 0:
                present = True

        if present:
            self.markPresent()

        Module.OK = Module.OK and present

        return present

class DownloadableModule(Module):
    def askDownload(self):
        reply = None
        while not reply in ['y', 'n']:
            reply = raw_input('Do you want me to retrieve %s and install it into your project? ' % self.name)
            reply = reply.lower()[:1]
        return (reply == 'y')

class Tarball(DownloadableModule):
    def download(self):
        global TMPDIR
        tmpdir = TMPDIR

        shutil.rmtree(TMPDIR, True)
        os.makedirs(TMPDIR)

        tb = os.path.join(TMPDIR, 'django-tarball.tgz')
        tarball = self.url[:]
        tarball = urllib2.Request(tarball)
        opener = urllib2.build_opener()
        tarball = opener.open(tarball).url
        urllib.URLopener().retrieve(tarball, tb)

        cwd = os.getcwd()
        os.chdir(TMPDIR)
        os.system('tar xvzf "%(tb)s"' % locals())
        os.chdir(cwd)

        subdir = self.subdir
        if subdir:
            print '%(tmpdir)s/%(subdir)s' % locals(), self.name
            shutil.move('%(tmpdir)s/%(subdir)s' % locals(), self.name)
        else:
            shutil.move(TMPDIR, self.name)
        shutil.rmtree(TMPDIR, True)

class SVN(DownloadableModule):
    def download(self):
        url = self.url
        name = self.name
        if self.subdir:
            if not self.subdir.startswith('/'):
                url = url + '/' + self.subdir
            else:
                url = url + self.subdir
        os.system('svn checkout %(url)s %(name)s' % locals())

class Accounts(DownloadableModule):
    def download(self):
        os.system('python manage.py startapp accounts')
        shutil.copyfile('agilito/install/accounts/urls.py', 'accounts/urls.py')
        os.mkdir('accounts/templates')
        shutil.copyfile('agilito/install/accounts/login.html', 'accounts/templates/login.html')
        shutil.copyfile('agilito/install/accounts/logout.html', 'accounts/templates/logout.html')

class BZR(DownloadableModule):
    def download(self):
        global TMPDIR
        tmpdir = TMPDIR

        url = self.url
        name = self.name
        subdir = self.subdir

        shutil.rmtree(TMPDIR, True)
        os.system('bzr export %(tmpdir)s %(url)s' % locals())
        if subdir:
            shutil.move('%(tmpdir)s/%(subdir)s' % locals(), name)
        else:
            shutil.move('%(tmpdir)s', name)
        shutil.rmtree(TMPDIR, True)

class GIT(DownloadableModule):
    def download(self):
        global TMPDIR
        tmpdir = TMPDIR

        url = self.url
        name = self.name
        subdir = self.subdir
        branch = self.branch

        shutil.rmtree(TMPDIR, True)
        os.system('git clone %(url)s %(tmpdir)s' % locals())
        if branch:
            cwd = os.getcwd()
            os.chdir(TMPDIR)
            print 'Fetching git branch'
            os.system('git checkout -b %(branch)s origin/%(branch)s' % locals())
            os.chdir(cwd)
            
        if subdir:
            shutil.move('%(tmpdir)s/%(subdir)s' % locals(), name)
        else:
            shutil.move(TMPDIR, name)
        shutil.rmtree(TMPDIR, True)

Module('django', url = 'http://www.djangoproject.com/', app=False).verify()
Module('html5lib', url = 'http://code.google.com/p/html5lib/', app=False).verify()
for app in ['admin', 'humanize', 'markup']:
    Module('django.contrib.' + app).verify()

if config['debug']:
    Tarball('debug_toolbar',
        url='http://github.com/robhudson/django-debug-toolbar/tarball/0.8.0',
        subdir='robhudson-django-debug-toolbar-4f43c9b/debug_toolbar/').verify()

Module('dulwich', url='http://samba.org/~jelmer/dulwich/', app=False, optional=True).verify()

SVN('queryutils', url = 'http://agilito.googlecode.com/svn/trunk/queryutils').verify()

SVN('tagging', url = 'http://django-tagging.googlecode.com/svn/trunk/tagging').verify()

Tarball('threadedcomments',
    url='http://django-threadedcomments.googlecode.com/files/django-threadedcomments-0.5.1.tar.gz',
    subdir='django-threadedcomments-0.5.1/threadedcomments').verify()

Tarball('odf',
    url='http://forge.osor.eu/frs/download.php/552/odfpy-0.9.1.tar.gz',
    subdir='odfpy-0.9.1/odf',
    app=False).verify()

Accounts('accounts').verify()

Module('django_extensions', url='http://code.google.com/p/django-command-extensions', optional=True).verify()

import settings

for app in Module.required:
    if not app in Module.available:
        print 'Missing required app', app
        Module.OK = False

for app in Module.apps:
    if not app in settings.INSTALLED_APPS:
        Module.OK = False
        print "Please add '%(app)s' to your INSTALLED_APPS in your settings.py" % locals()

if not 'django_extensions' in Module.available or not 'django_extensions' in settings.INSTALLED_APPS:
    print """
If you install django_extensions
    (http://code.google.com/p/django-command-extensions)
I can inspect the database for changes against the models"""
elif not config['nosqldiff']:
    diff = call('python manage.py sqldiff agilito')
    syncdb = False
    applydiff = False
    for l in diff.split('\n'):
        l = l.strip().lower()
        if not l:
            continue
        if l in ['begin;', 'commit;']:
            continue

        if l.startswith('-- table missing'):
            syncdb = True
        elif not l.startswith('--'):
            applydiff = True

    if applydiff:
        print 'The following changes need to be applied to your database:'
        print diff
    if syncdb:
        print "You have missing tables. Please re-run 'python manage.py syncdb'"
    Module.OK = Module.OK and not (applydiff or syncdb)

if not 'PRINTABLE_CARD_STOCK' in dir(settings):
    print """Please add the following to %(installdir)s/settings.py:
PRINTABLE_CARD_STOCK = 'Buro1 129820' # choose appropriate card stock
""" % locals()
    Module.OK = False

if not 'LOGIN_REDIRECT_URL' in dir(settings) or settings.LOGIN_REDIRECT_URL != '/':
    print 'Please set LOGIN_REDIRECT_URL to "/" in %(installdir)s/settings.py' % locals()
    Module.OK = False

from django.db import connection, backend
intro = backend.DatabaseIntrospection(connection)
cursor = connection.cursor()
if 'planned' in [str(col[0]) for col in intro.get_table_description(cursor, 'agilito_userstory')]:
    print
    print '*** IMPORTANT ***'
    print '"planned" has been replaced by "size" in table agilito_userstory'
    print 'If you use "planned" to register unrestricted sizes, you need to upgrade manually:'
    print '   update agilito_userstory set size=planned'
    print '   alter table agilito_userstory drop planned'
    print 'and then set UNRESTRICTED_SIZE to True in your settings'

needsdelete = False
for s, p in [('UserStory', 'UserStories'), ('Task', 'Tasks')]:
    cursor.execute('select count(1) from agilito_%s where state=1' % s.lower())

    if cursor.fetchone()[0]:
        needsdelete = True
        Module.OK = False
        print 'You have one or more archived %(p)s (state=1); %(s)s archival has been depracated, you will have to delete these from the database' % locals()
if needsdelete:
    print """the following SQL will do the trick:
delete from agilito_impediment_tasks
where task_id in (
    select id from agilito_task
    where state = 1 or exists(
        select 1 from agilito_userstory s
        where s.id = user_story_id and s.state = 1)
    )
;

delete from agilito_tasklog
where task_id in (
    select id from agilito_task
    where state = 1 or exists(
        select 1 from agilito_userstory s
        where s.id = user_story_id and s.state = 1)
    )
;

delete from agilito_task
where state = 1 or exists(
    select 1 from agilito_userstory s
    where s.id = user_story_id and s.state = 1)
;

delete from agilito_userstory where state = 1
;
"""

if config['debug']:
    debug_errors = False
    try:
        settings.INTERNAL_IPS
    except:
        print 'You need to set INTERNAL_IPS'
        debug_errors = True
    try:
        if not 'debug_toolbar.middleware.DebugToolbarMiddleware' in settings.MIDDLEWARE_CLASSES:
            print 'You need to add debug_toolbar.middleware.DebugToolbarMiddleware to your MIDDLEWARE_CLASSES'
            debug_errors = True
    except:
        debug_errors = True

    if debug_errors:
        print 'See documentation at http://github.com/robhudson/django-debug-toolbar'
        Module.OK = False

if not Module.OK:
    print
    print 'Please fix the issues reported and re-run the installer'
    sys.exit()
else:
    print
    print "You should be good to go. Edit your settings.py a and run 'python manage.py syncdb'"

if config['apache']:
    import socket
    import django
    fqdn = socket.getfqdn()
    adminmedia = django.__path__[0] + '/contrib/admin/media'
    print """
You can run Agilito from Apache using the following site config:


<VirtualHost *>
    ServerName %(fqdn)s
    DocumentRoot "%(installdir)s"
    <Location />
        SetHandler python-program
        PythonHandler django.core.handlers.modpython
        SetEnv DJANGO_SETTINGS_MODULE settings
        PythonPath "['%(installdir)s'] + sys.path"
    </Location>
    Alias /media/ "%(adminmedia)s"
    <Location /media/>
        SetHandler none
    </Location>
    Alias /agilito/ "%(installdir)s/agilito/media/"
    <location /agilito/>
        SetHandler none
    </Location>
</VirtualHost>""" % locals()
