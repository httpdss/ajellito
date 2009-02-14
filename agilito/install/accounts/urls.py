from django.conf.urls.defaults import *

urlpatterns = patterns('',
    # Django "batteries included".
    (r'^login/$', 'django.contrib.auth.views.login', {'template_name': 'login.html'}),
    (r'^logout/$', 'django.contrib.auth.views.logout', {'template_name': 'logout.html'}),
    (r'^changepassword/?$', 'django.contrib.auth.views.password_change', {'post_change_redirect': '/'}),
)
