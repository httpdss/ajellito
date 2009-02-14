#!/usr/bin/env python

import sys, os

if len(sys.argv) > 1:
    projectname = sys.argv[1]
else:
    projectname = '..'

installdir = os.path.abspath(projectname)

complete = True

if not os.path.exists(installdir):
    os.system('django-admin startproject %(projectname)s' % locals())
    file(os.path.join(installdir, 'urls.py'), 'w').write("""
from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    # (r'^agilitoproject/', include('agilitoproject.foo.urls')),

    # Uncomment the admin/doc line below and add
    # 'django.contrib.admindocs'
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/',
    # include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # (r'^admin/(.*)', admin.site.root),
    (r'^accounts/', include('accounts.urls')),
    (r'', include('agilito.urls')),
    (r'^admin/(.*)', admin.site.root),

)
""")
    file(os.path.join(installdir, 'settings.patch'), 'w').write("""--- org/settings.py	2009-01-31 13:29:37.000000000 +0100
+++ %(projectname)s/settings.py	2009-01-31 13:22:09.000000000 +0100
@@ -9,8 +9,8 @@
 
 MANAGERS = ADMINS
 
-DATABASE_ENGINE = ''           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
-DATABASE_NAME = ''             # Or path to database file if using sqlite3.
+DATABASE_ENGINE = 'sqlite3'           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
+DATABASE_NAME = 'agilito.db'             # Or path to database file if using sqlite3.
 DATABASE_USER = ''             # Not used with sqlite3.
 DATABASE_PASSWORD = ''         # Not used with sqlite3.
 DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
@@ -76,4 +76,18 @@
     'django.contrib.contenttypes',
     'django.contrib.sessions',
     'django.contrib.sites',
+    'django.contrib.admin',
+    'django.contrib.humanize',
+    'django.contrib.markup',
+    'agilito',
+    'queryutils',
+    'accounts',
+    'tagging',
 )
+
+CARD_INFO = {
+    'ini': '%(installdir)s/ODTLabels.ini',
+    'spec': 'Buro1 129820',
+    'template': '%(installdir)s/agilito/templates/template.odt'
+}
+
""" % locals())
    os.system('patch -p0 < %(installdir)s/settings.patch' % locals())

if not os.path.exists(os.path.join(installdir, 'manage.py')):
    print '%(installdir)s is not a django project' % locals()
    complete = False

sys.path.append(installdir)
os.chdir(installdir)

try:
    import pyExcelerator
except ImportError:
    print 'You need to have pyExcelerator installed'
    print 'pyExcelerator is available at http://sourceforge.net/projects/pyexcelerator'
    complete = False

try:
    import queryutils
except ImportError:
    print 'You need to have queryutils installed'
    print 'queryutils is available at http://trac.ifpeople.net/products/browser/queryutils'
    reply = None
    while not reply in ['y', 'n']:
        reply = raw_input('Do you want me to install it into your project (y/n)?')
        reply = reply.lower()[:1]
    if reply == 'y':
        # os.system('svn checkout http://opensource.ifpeople.net/svn/queryutils/trunk/src/queryutils queryutils')
        os.system('svn checkout https://air.googlecode.com/svn/trunk/queryutils queryutils')

    complete = False

try:
    import matplotlib
except ImportError:
    print 'You need to have matplotlib installed'
    print 'matplotlib is available at http://matplotlib.sourceforge.net/'
    complete = False

try:
    import django
except ImportError:
    print 'You need to have django installed'
    print 'django is available at http://www.djangoproject.com/'
    complete = False

try:
    import agilito
except ImportError:
    print 'You need to have agilito installed'
    print 'Agilito is available at http://air.googlecode.com/'
    reply = None
    while not reply in ['y', 'n']:
        reply = raw_input('Do you want me to install it into your project (y/n)?')
        reply = reply.lower()[:1]
    if reply == 'y':
        os.system('svn checkout https://air.googlecode.com/svn/trunk/agilito agilito')

    complete = False

try:
    import tagging
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

        complete = False

def setup_accounts():
    os.system('python manage.py startapp accounts')

    open('accounts/urls.py', 'w').write("""
from django.conf.urls.defaults import *

urlpatterns = patterns('',
    # Django "batteries included".
    (r'^login/$', 'django.contrib.auth.views.login', {'template_name': 'login.html'}),
    (r'^logout/$', 'django.contrib.auth.views.logout', {'template_name': 'logout.html'}),
)
""")
    os.mkdir('accounts/templates')

    file('accounts/templates/login.html', 'w').write("""
{% extends "master.html" %}

{%block css%}
<style type="text/css">
#content form{
width:50%;
margin:0 auto;
border: 1px solid #EBEBEB;
padding:10px;
}

</style>
{%endblock%}

{% block content %}
<div id="login-form">
<h2>Please login</h2>
{% if form.errors %}
<p id="error-message">Username / password combination does not
exist</p>
{% endif %}

<form method="post" action=".">
{% include 'generic_form.html' %}
<input type="hidden" name="next" value="{{ next }}" />
<input type="submit" value="login" />
</form>
</div>
{% endblock %}
""")
    file('accounts/templates/logout.html', 'w').write("""
{% extends "master.html" %}

{% block content %}

{% if form.errors %}
<p>Your username and password didn't match. Please try again.</p>
{% endif %}

<form method="post" action=".">
<h3>You are now logged out</h3>
</form>

{% endblock %}
""")

try:
    import accounts
except ImportError:
    print 'You need to have an accounts module'

    reply = None
    while not reply in ['y', 'n']:
        reply = raw_input('Do you want me to install the default django version?')
        reply = reply.lower()[:1]
    if reply == 'y':
        setup_accounts()
    complete = False

installed_apps = None
for l in open('settings.py').readlines():
    if l.startswith('INSTALLED_APPS'):
        installed_apps = []
    elif not installed_apps is None and l.startswith(')'):
        break
    elif not installed_apps is None:
        app = l.replace("'", '').replace('"', '').replace(',', '').strip()
        installed_apps.append(app)
required_apps = [   'django.contrib.admin', 'django.contrib.humanize', 'django.contrib.markup',
                    'agilito', 'queryutils', 'accounts', 'tagging']
if installed_apps is None:
    installed_apps = []

for app in required_apps:
    if not app in installed_apps:
        complete = False
        print "Please add '%(app)s' to your INSTALLED_APPS in your settings.py" % locals()

if not complete:
    print 'Pleased address the dependencies above and re-run the install script'
else:
    print "You should be good to go. Edit your settings.py a and run 'python manage.py syncdb'"
