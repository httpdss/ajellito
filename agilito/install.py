#!/usr/bin/env python

import sys, os, shutil

if len(sys.argv) > 1:
    projectname = sys.argv[1]
else:
    projectname = '..'

installdir = os.path.abspath(projectname)

complete = True
fresh = not os.path.exists(installdir)

if fresh:
    os.system('django-admin startproject %(projectname)s' % locals())

if not os.path.exists(os.path.join(installdir, 'manage.py')):
    print '%(installdir)s is not a django project' % locals()
    sys.exit()

sys.path.append(installdir)
os.chdir(installdir)

def rerun(msg = None):
    print
    if msg: print msg
    print 'Please re-run the installer'
    sys.exit()

try:
    import django
    print 'django is present'
except ImportError:
    print 'You need to have django installed'
    print 'django is available at http://www.djangoproject.com/'
    rerun()

try:
    import agilito
    print 'Agilito is present'
except ImportError:
    print 'You need to have agilito installed'
    print 'Agilito is available at http://agilito.googlecode.com/'
    reply = None
    while not reply in ['y', 'n']:
        reply = raw_input('Do you want me to install it into your project (y/n)?')
        reply = reply.lower()[:1]
    if reply == 'y':
        os.system('svn checkout https://agilito.googlecode.com/svn/trunk/agilito agilito')

    rerun()

if fresh:
    print 'Installing default url redirector'
    shutil.copyfile('agilito/install/urls.py', 'urls.py')
    
try:
    import pyExcelerator
    print 'pyExcelerator is present'
except ImportError:
    print 'You need to have pyExcelerator installed'
    print 'pyExcelerator is available at http://sourceforge.net/projects/pyexcelerator'
    rerun()

try:
    import queryutils
    print 'queryutils is present'
except ImportError:
    print 'You need to have queryutils installed'
    print 'queryutils is available at http://trac.ifpeople.net/products/browser/queryutils'
    reply = None
    while not reply in ['y', 'n']:
        reply = raw_input('Do you want me to install it into your project (y/n)?')
        reply = reply.lower()[:1]
    if reply == 'y':
        os.system('svn checkout https://agilito.googlecode.com/svn/trunk/queryutils queryutils')

    rerun()

try:
    import matplotlib
    print 'matplotlib is present'
except ImportError:
    print 'You need to have matplotlib installed'
    print 'matplotlib is available at http://matplotlib.sourceforge.net/'
    rerun()


try:
    import tagging
    print 'tagging is present'
except ImportError, e:
    if str(e).find('DJANGO_SETTINGS_MODULE') < 0:
        print 'You need to have django-tagging installed'
        print 'Django-tagging is available at http://django-tagging.googlecode.com/'
        reply = None
        while not reply in ['y', 'n']:
            reply = raw_input('Do you want me to install it into your project (y/n)?')
            reply = reply.lower()[:1]
        if reply == 'y':
            os.system('svn checkout http://django-tagging.googlecode.com/svn/trunk/tagging tagging')

        rerun()

try:
    import accounts
    print 'accounts is present'
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

    rerun()

import settings
required_apps = [   'django.contrib.admin', 'django.contrib.humanize', 'django.contrib.markup',
                    'agilito', 'queryutils', 'accounts', 'tagging']

apps_installed = True
for app in required_apps:
    if not app in settings.INSTALLED_APPS:
        apps_installed = False
        print "Please add '%(app)s' to your INSTALLED_APPS in your settings.py" % locals()
if not apps_installed:
    rerun()

if not 'CARD_INFO' in dir(settings):
    print """Please add the following to %(installdir)s/settings.py:
CARD_INFO = {
    'ini': '%(installdir)s/agilito/ODTLabels.ini',
    'spec': 'Buro1 129820',
    'template': '%(installdir)s/agilito/templates/template.odt'
}
""" % locals()
    rerun()

if not 'LOGIN_REDIRECT_URL' in dir(settings) or settings.LOGIN_REDIRECT_URL != '/':
    print 'Please set LOGIN_REDIRECT_URL to "/" in %(installdir)s/settings.py' % locals()
    rerun()

print
print "You should be good to go. Edit your settings.py a and run 'python manage.py syncdb'"
