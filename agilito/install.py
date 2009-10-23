#!/usr/bin/env python

import sys, os, shutil, re
from distutils.sysconfig import get_python_lib
import tempfile
import uuid
import getopt

try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["install=", "apache", "nosqldiff"])
except getopt.GetoptError, err:
    print str(err)
    sys.exit(1)

config = {'install': 'ask', 'apache': False, 'nosqldiff': False}
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
            print 'If you install %s you will get additional features in Agilito' % self.name
        else:
            print 'You need to have %s installed' % self.name

        Module.OK = Module.OK and self.optional

        do_download = False
        do_download = do_download or (config['install'] == 'ask' and self.askDownload())
        do_download = do_download or config['install'] == 'auto'
        if not do_download:
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

        return present

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
for app in ['admin', 'humanize', 'markup']:
    Module('django.contrib.' + app).verify()

Module('pyExcelerator',
    url = 'http://sourceforge.net/projects/pyexcelerator',
    app = False,
    optional=True).verify()

SVN('agilito', url = 'http://agilito.googlecode.com/svn/trunk/agilito').verify()

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
elif not config['nosqldiff']:
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
