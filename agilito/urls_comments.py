from django.conf.urls.defaults import *
from django.contrib import admin
from django.contrib.auth.decorators import login_required

admin.autodiscover()

import os

urlpatterns = patterns('agilito.threadedcommentsviews',
    ### Comments ###
    url(r'^comment/(?P<content_type>\d+)/(?P<object_id>\d+)/$', 'comment', name="tc_comment"),
    url(r'^comment/(?P<content_type>\d+)/(?P<object_id>\d+)/(?P<parent_id>\d+)/$', 'comment', name="tc_comment_parent"),
    url(r'^comment/(?P<object_id>\d+)/delete/$', 'comment_delete', name="tc_comment_delete"),
    url(r'^comment/(?P<edit_id>\d+)/edit/$', 'comment', name="tc_comment_edit"),
    
    ### Comments (AJAX) ###
    url(r'^comment/(?P<content_type>\d+)/(?P<object_id>\d+)/(?P<ajax>json|xml)/$', 'comment', name="tc_comment_ajax"),
    url(r'^comment/(?P<content_type>\d+)/(?P<object_id>\d+)/(?P<parent_id>\d+)/(?P<ajax>json|xml)/$', 'comment', name="tc_comment_parent_ajax"),
    url(r'^comment/(?P<edit_id>\d+)/edit/(?P<ajax>json|xml)/$', 'comment', name="tc_comment_edit_ajax"),
)
