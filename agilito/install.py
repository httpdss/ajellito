#!/usr/bin/env python

import sys, os, shutil, re
from distutils.sysconfig import get_python_lib

os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

if len(sys.argv) > 1:
    projectname = sys.argv[1]
else:
    projectname = '..'

installdir = os.path.abspath(projectname)

complete = True
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

complete = True
def rerun(msg = None):
    print
    if msg: print msg
    print 'Please re-run the installer'
    sys.exit()

required_apps = ['django.contrib.admin', 'django.contrib.humanize', 'django.contrib.markup', 'accounts' ]

class Project:
    required = ['django.contrib.admin',
                'django.contrib.humanize',
                'django.contrib.markup',
                'accounts' ]
    OK = True

    def __init__(self, name, **kwargs):
        self.name = name
        self.optional = False
        self.app = True
        self.url = None
        self.subdir = None
        self.branch = None

        for k, v in kwargs.items():
            setattr(self, k, v)

    def askDownload(self):
        return True

    def download(self):
        print '%s is available at %s' % (self.name, self.url)

    def verify(self):
        if not self.optional and self.app:
            Project.required.append(self.name)

        try:
            __import__(self.name)
            print '** %s is present' % self.name
            return True
        except ImportError, e:
            if str(e).find('DJANGO_SETTINGS_MODULE') >= 0:
                return True

        if self.optional:
            print 'If you install %s you will get additional features in Agilito' % self.name
        else:
            print 'You need to have %s installed' % self.name

        Project.OK = Project.OK and self.optional

        if self.askDownload():
            self.download()

class DownloadableProject(Project):
    def askDownload(self):
        reply = None
        while not reply in ['y', 'n']:
            reply = raw_input('Do you want me to retrieve %s and install it into your project? ' % self.name)
            reply = reply.lower()[:1]
        return (reply == 'y')

class SVN(DownloadableProject):
    def download(self):
        url = self.url
        name = self.name
        if self.subdir:
            if not self.subdir.startswith('/'):
                url = url + '/' + self.subdir
            else:
                url = url + self.subdir
        os.system('svn checkout %(url)s %(name)s' % locals())
        
class BZR(DownloadableProject):
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

class GIT(DownloadableProject):
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

def verify(name, url, vcs=None, app=True, optional=False):
    global required_apps, complete

    if not optional and app:
        required_apps.append(name)

    try:
        __import__(name)
        print '** %s is present' % name
        return True
    except ImportError, e:
        if str(e).find('DJANGO_SETTINGS_MODULE') >= 0:
            return

        if optional:
            print 'If you install %s you will get additional features in Agilito' % name
        else:
            print 'You need to have %s installed' % name

        if url:
            print '%s is available at %s' % (name, url)
        if url and vcs:
            reply = None
            while not reply in ['y', 'n']:
                reply = raw_input('Do you want me to retrieve %s and install it into your project? ' % name)
                reply = reply.lower()[:1]
            if reply == 'y':
                os.system(supported_vcs[vcs] % locals())

        complete = complete and optional
        return False

if not Project('django', url = 'http://www.djangoproject.com/', app=False).verify():
    rerun()

Project('pyExcelerator',
    url = 'http://sourceforge.net/projects/pyexcelerator',
    optional=True).verify()

Project('matplotlib',
    url = 'http://matplotlib.sourceforge.net/',
    optional=True).verify()

if not SVN('agilito', url = 'http://agilito.googlecode.com/svn/trunk/agilito').verify():
    rerun()

if fresh:
    print 'Installing default url redirector'
    shutil.copyfile('agilito/install/urls.py', 'urls.py')

SVN('queryutils', url = 'http://agilito.googlecode.com/svn/trunk/queryutils').verify()

SVN('tagging', url = 'http://django-tagging.googlecode.com/svn/trunk/tagging').verify()

Project('threadedcomments',
    url = 'http://code.google.com/p/django-threadedcomments/').verify()

#BZR('wiki', url = 'lp:django-wikiapp', subdir = 'wiki').verify()
#GIT('wakawaka', url = 'git://github.com/brosner/django-wakawaka.git', branch = 'pinax-group-support', subdir = 'src/wakawaka').verify()

try:
    import accounts
    print '** accounts is present'
except ImportError:
    print 'You need to have an accounts module'

    reply = None
    while not reply in ['y', 'n']:
        reply = raw_input('Do you want me to install the default django version?')
        reply = reply.lower()[:1]
    if reply == 'y':
        os.system('python manage.py startapp accounts')
        shutil.copyfile('agilito/install/accounts/urls.py', 'accounts/urls.py')
        os.mkdir('accounts/templates')
        shutil.copyfile('agilito/install/accounts/login.html', 'accounts/templates/login.html')
        shutil.copyfile('agilito/install/accounts/logout.html', 'accounts/templates/logout.html')

    Project.OK = False

import settings

apps_installed = True
for app in Project.required:
    if not app in settings.INSTALLED_APPS:
        apps_installed = False
        print "Please add '%(app)s' to your INSTALLED_APPS in your settings.py" % locals()
if not apps_installed:
    Project.OK = False

if not 'PRINTABLE_CARD_STOCK' in dir(settings):
    print """Please add the following to %(installdir)s/settings.py:
PRINTABLE_CARD_STOCK = 'Buro1 129820' # choose appropriate card stock
""" % locals()
    Project.OK = False

if not 'LOGIN_REDIRECT_URL' in dir(settings) or settings.LOGIN_REDIRECT_URL != '/':
    print 'Please set LOGIN_REDIRECT_URL to "/" in %(installdir)s/settings.py' % locals()
    Project.OK = False

################ upgrade database
if not verify('django_extensions', 'http://code.google.com/p/django-command-extensions', optional=True):
    print 'If you install django_extensions (http://code.google.com/p/django-command-extensions) I can inspect the database for changes against the models'
elif not 'django_extensions' in settings.INSTALLED_APPS:
    print 'django_extensions is not included in INSTALLED_APPS'
else:
    print 'Installer has detected the following changes pending for your database:'
    os.system('python manage.py sqldiff agilito')

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

if complete:
    print
    print "You should be good to go. Edit your settings.py a and run 'python manage.py syncdb'"
else:
    rerun()

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
