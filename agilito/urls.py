from django.conf.urls.defaults import *
from django.contrib import admin
from agilito.feeds import Backlog, Iteration

admin.autodiscover()

import os

media_root = os.path.join(os.path.dirname(__file__), 'media')

feeds = {
    'backlog': Backlog,
    'iteration': Iteration,
    }

urlpatterns = patterns('agilito.views',
    (r'^$', 'index'),

    (r'^(?P<project_id>\d+)/backlog/$', 'backlog'),
    (r'^(?P<project_id>\d+)/backlog/(?P<states>\d+(:\d+)*)/$', 'backlog'),
    (r'^(?P<project_id>\d+)/product_backlog/$', 'product_backlog'),
    url(r'^(?P<project_id>\d+)/product_backlog/(?P<states>\d+(:\d+)*)/$', 'product_backlog', name='product_backlog_for_states'),
    url(r'^(?P<project_id>\d+)/backlog/userstory/add/$', 'userstory_create', name="story_from_backlog"),
    url(r'^(?P<project_id>\d+)/backlog/save/$', 'backlog_save', name="backlog_save"),

    url(r'^(?P<project_id>\d+)/release/add/$', 'release_create', name="release_create"),
    url(r'^(?P<project_id>\d+)/release/(?P<release_id>\d+)/edit/$', 'release_edit', name='release_edit'),
    (r'^(?P<project_id>\d+)/release/(?P<release_id>\d+)/delete/$', 'release_delete'),
    
    url(r'^(?P<project_id>\d+)/iteration/$', 'iteration_status', name="current_iteration_status"),
    url(r'^(?P<project_id>\d+)/iteration/(?P<iteration_id>\d+)/$', 'iteration_status', name="iteration_status_with_id"),
    (r'^(?P<project_id>\d+)/iteration/import/$', 'iteration_import'),
    url(r'^(?P<project_id>\d+)/iteration/add/$', 'iteration_create', name="iteration_create"),
    url(r'^(?P<project_id>\d+)/iteration/(?P<iteration_id>\d+)/edit/$', 'iteration_edit', name='iteration_edit'),
    (r'^(?P<project_id>\d+)/iteration/(?P<iteration_id>\d+)/delete/$', 'iteration_delete'),

    url(r'^(?P<project_id>\d+)/taskboard/(?P<iteration_id>\d+)/$', 'taskboard', name="taskboard"),
    url(r'^(?P<project_id>\d+)/iteration/(?P<iteration_id>\d+)/userstory/add/$', 'userstory_create', name="story_from_iteration"),
    
    url(r'^(?P<project_id>\d+)/iteration/hours/$', 'iteration_hours', name="current_iteration_hours"),
    url(r'^(?P<project_id>\d+)/iteration/(?P<iteration_id>\d+)/hours/$', 'iteration_hours', name="itertion_hours_with_id"),
    (r'^(?P<project_id>\d+)/iteration/(?P<iteration_id>\d+)/hours_export/$', 'hours_export'),
    (r'^(?P<project_id>\d+)/iteration/(?P<iteration_id>\d+)/burndown_data/$', 'iteration_burndown_data'),
    (r'^(?P<project_id>\d+)/iteration/(?P<iteration_id>\d+)/cards/$', 'iteration_cards'),
    (r'^(?P<project_id>\d+)/iteration/(?P<iteration_id>\d+)/status_table/$', 'iteration_status_table'),
    (r'^(?P<project_id>\d+)/iteration/(?P<iteration_id>\d+)/export/$', 'iteration_export'),
    (r'^(?P<project_id>\d+)/iteration/(?P<iteration_id>\d+)/burndown_chart/(?P<name>[a-z0-9]+)[.]png$', 'iteration_burndown_chart'),
    (r'^(?P<project_id>\d+)/iteration/(?P<iteration_id>\d+)/impediment/add/$', 'impediment_create'),
    url(r'^(?P<project_id>\d+)/iteration/(?P<iteration_id>\d+)/impediment/(?P<impediment_id>\d+)/edit/$', 'impediment_edit', name='impediment_edit'),
    (r'^(?P<project_id>\d+)/product_backlog_chart/(?P<iteration_id>.*)$', 'product_backlog_chart'),

    (r'^(?P<project_id>\d+)/userstory/(?P<userstory_id>\d+)/$', 'userstory_detail'),
    (r'^(?P<project_id>\d+)/userstory/(?P<userstory_id>\d+)/delete/$', 'userstory_delete'),
    (r'^(?P<project_id>\d+)/userstory/(?P<userstory_id>\d+)/edit/$', 'userstory_edit'),
    (r'^(?P<project_id>\d+)/userstory/(?P<userstory_id>\d+)/move/$', 'userstory_move'),

    (r'^(?P<project_id>\d+)/userstory/(?P<userstory_id>\d+)/task/add/$', 'task_create'),
    (r'^(?P<project_id>\d+)/userstory/(?P<userstory_id>\d+)/task/(?P<task_id>\d+)/edit/$', 'task_edit'),
    (r'^(?P<project_id>\d+)/userstory/(?P<userstory_id>\d+)/task/(?P<task_id>\d+)/$', 'task_detail'),
    (r'^(?P<project_id>\d+)/userstory/(?P<userstory_id>\d+)/task/(?P<task_id>\d+)/delete/$', 'task_delete'),


    (r'^(?P<project_id>\d+)/userstory/(?P<userstory_id>\d+)/attachment/add/$', 'add_attachment'),
    #just left it for the record.
    #(r'^(?P<project_id>\d+)/userstory/(?P<userstory_id>\d+)/attachment/(?P<attachment_id>\d+)/edit/$', 'edit_attachment'),
    (r'^(?P<project_id>\d+)/userstory/(?P<userstory_id>\d+)/attachment/(?P<attachment_id>\d+)/delete/$', 'delete_attachment'),
    
    (r'^(?P<project_id>\d+)/userstory/(?P<userstory_id>\d+)/testcase/add/$', 'testcase_create'),
    (r'^(?P<project_id>\d+)/userstory/(?P<userstory_id>\d+)/testcase/(?P<testcase_id>\d+)/edit/$', 'testcase_edit'),
    (r'^(?P<project_id>\d+)/userstory/(?P<userstory_id>\d+)/testcase/(?P<testcase_id>\d+)/$', 'testcase_detail'),
    (r'^(?P<project_id>\d+)/userstory/(?P<userstory_id>\d+)/testcase/(?P<testcase_id>\d+)/delete/$', 'testcase_delete'),

    url(r'^(?P<project_id>\d+)/userstory/(?P<userstory_id>\d+)/testcase/(?P<testcase_id>\d+)/testresult/(?P<testresult_id>\d+)/$', 'testresult_detail', name='testresult_detail_with_id'),
    (r'^(?P<project_id>\d+)/userstory/(?P<userstory_id>\d+)/testcase/(?P<testcase_id>\d+)/testresult/add/$', 'testresult_create'),
    (r'^(?P<project_id>\d+)/userstory/(?P<userstory_id>\d+)/testcase/(?P<testcase_id>\d+)/testresult/(?P<testresult_id>\d+)/edit/$', 'testresult_edit'),
    (r'^(?P<project_id>\d+)/userstory/(?P<userstory_id>\d+)/testcase/(?P<testcase_id>\d+)/testresult/(?P<testresult_id>\d+)/delete/$', 'testresult_delete'),

    (r'^(?P<project_id>\d+)/search/', 'search'),
    (r'^json/task/[ra]?(?P<task_id>\d+)/$', 'task_json'),

    (r'^(?P<project_id>\d+)/log/$', 'timelog'),
    (r'^(?P<project_id>\d+)/log/task/(?P<task_id>\d+)/$', 'timelog_task'),

    (r'^close/$', 'close_window'),

    url(r'^csv/', 'csv_log_all_projects', name='timelogs_for_all_projects'),
    url(r'^(?P<project_id>\d+)/csv/(?P<username>[A-Za-z0-9_]+)/', 'csv_log', name='timelogs_for_user_in_project'),
    url(r'^(?P<project_id>\d+)/csv/', 'csv_log_for_project', name='timelogs_for_project'),

)

urlpatterns += patterns('',
    (r'^admin/(.*)', admin.site.root),
    (r'^agilito/(?P<path>.*)$', 'django.views.static.serve', {'document_root': media_root}),
    (r'^xmlrpc/', 'agilito.xmlrpc.xmlrpc.view', {'module':'agilito.xmlrpc'}),
    (r'^(rsd.xml)$', 'django.views.static.serve', {'document_root': media_root}),

    (r'^feeds/(?P<url>.*)/$', 'agilito.feeds.feed', {'feed_dict': feeds}),
)

