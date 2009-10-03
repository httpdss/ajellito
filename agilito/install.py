#!/usr/bin/env python

import sys, os, shutil, re
from distutils.sysconfig import get_python_lib

os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

if len(sys.argv) > 1:
    projectname = sys.argv[1]
else:
    projectname = '..'

installdir = os.path.abspath(projectname)

fresh = not os.path.exists(installdir)

if fresh:
    da = 'django/bin/django-admin.py'
    django_admin = None
    for d in sys.path:
        candidate = os.path.join(d, da)
        print candidate
        if os.path.exists(candidate):
            django_admin = candidate
            break
    if django_admin is None:
        print 'I cannot find django-admin.py'
        sys.exit()

    py = sys.executable
    os.system('%(py)s %(django_admin)s startproject %(projectname)s' % locals())

if not os.path.exists(os.path.join(installdir, 'manage.py')):
    print '%(installdir)s is not a django project' % locals()
    sys.exit()

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

    def verify(self):
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
            print '** %s is present' % self.name
            if self.app:
                Module.apps.append(self.name)
            Module.available.append(self.name)
            return True

        if self.optional:
            print 'If you install %s you will get additional features in Agilito' % self.name
        else:
            print 'You need to have %s installed' % self.name

        Module.OK = Module.OK and self.optional

        if self.askDownload():
            self.download()

class DownloadableModule(Module):
    def askDownload(self):
        reply = None
        while not reply in ['y', 'n']:
            reply = raw_input('Do you want me to retrieve %s and install it into your project? ' % self.name)
            reply = reply.lower()[:1]
        return (reply == 'y')

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
        url = self.url
        name = self.name
        subdir = self.subdir

        shutil.rmtree('_bzrco', True)
        os.system('bzr export _bzrco %(url)s' % locals())
        if subdir:
            shutil.move('_bzrco/%(subdir)s' % locals(), name)
        else:
            shutil.move('_bzrco', name)
        shutil.rmtree('_bzrco', True)

class GIT(DownloadableModule):
    def download(self):
        url = self.url
        name = self.name
        subdir = self.subdir
        branch = self.branch
        codir = '_gitco'

        shutil.rmtree('_gitco', True)
        os.system('git clone %(url)s %(codir)s' % locals())
        if branch:
            cwd = os.getcwd()
            os.chdir(codir)
            print 'Fetching git branch'
            os.system('git checkout -b %(branch)s origin/%(branch)s' % locals())
            os.chdir(cwd)
            
        if subdir:
            shutil.move('%(codir)s/%(subdir)s' % locals(), name)
        else:
            shutil.move(codir, name)
        shutil.rmtree(codir, True)

Module('django', url = 'http://www.djangoproject.com/', app=False).verify()
for app in ['admin', 'humanize', 'markup']:
    Module('django.contrib.' + app).verify()

Module('pyExcelerator',
    url = 'http://sourceforge.net/projects/pyexcelerator',
    app = False,
    optional=True).verify()

Module('matplotlib',
    url = 'http://matplotlib.sourceforge.net/',
    app = False,
    optional=True).verify()

SVN('agilito', url = 'http://agilito.googlecode.com/svn/trunk/agilito').verify()

if 'agilito' in Module.available and fresh:
    print 'Installing default url redirector'
    shutil.copyfile('agilito/install/urls.py', 'urls.py')

SVN('queryutils', url = 'http://agilito.googlecode.com/svn/trunk/queryutils').verify()

SVN('tagging', url = 'http://django-tagging.googlecode.com/svn/trunk/tagging').verify()

#Module('threadedcomments', url = 'http://code.google.com/p/django-threadedcomments/').verify()

#BZR('wiki', url = 'lp:django-wikiapp', subdir = 'wiki').verify()
#GIT('wakawaka', url = 'git://github.com/brosner/django-wakawaka.git', branch = 'pinax-group-support', subdir = 'src/wakawaka').verify()

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
else:
    print 'Installer has detected the following changes pending for your database:'
    os.system('python manage.py sqldiff agilito')

if not 'PRINTABLE_CARD_STOCK' in dir(settings):
    print """Please add the following to %(installdir)s/settings.py:
PRINTABLE_CARD_STOCK = 'Buro1 129820' # choose appropriate card stock
""" % locals()
    Module.OK = False

if not 'LOGIN_REDIRECT_URL' in dir(settings) or settings.LOGIN_REDIRECT_URL != '/':
    print 'Please set LOGIN_REDIRECT_URL to "/" in %(installdir)s/settings.py' % locals()
    Module.OK = False

if not Module.OK:
    print
    print 'Please fix the issues reported and re-run the installer'
    sys.exit()
else:
    print
    print "You should be good to go. Edit your settings.py a and run 'python manage.py syncdb'"

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
