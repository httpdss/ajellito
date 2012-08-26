from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url(r'^graphs/$', 'sprints.views.index', name="sprints-index"),
    url(r'^graphs/(?P<sprint_id>\d+)/detail/$', 'sprints.views.detail', name="sprints-detail"),
    url(r'^(?P<sprint_id>\d+)/browse/$', 'sprints.views.browse', name="sprints-browse"),
)
