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
    url(r'^$', 'index', name = "agilito_index"),

    (r'^(?P<project_id>\d+)/touch/$', 'touch_cache'),

    url(r"^projects/list/$", "project_list", name="project_list"),
    url(r"^projects/add/$", "project_create", name="project_create"),
    url(r"^projects/(?P<project_id>\d+)edit/$", "project_edit", name="project_edit"),
    url(r"^projects/(?P<project_id>\d+)delete/$", "project_delete", name="project_delete"),
    url(r"^projects/(?P<project_id>\d+)details/$", "project_details", name="project_delete"),

    url(r'^(?P<project_id>\d+)/backlog/$', 'backlog', name='product_backlog'),
    url(r'^(?P<project_id>\d+)/backlog/states=(?P<states>\d+(:\d+)*)/$', 'backlog', name='product_backlog_states'),
    url(r'^(?P<project_id>\d+)/backlog/states=(?P<states>\d+(:\d+)*)/suggest-(?P<suggest>actuals|estimates)/$', 'backlog',
        name='product_backlog_states_suggest'),

    (r'^(?P<project_id>\d+)/backlog/ods/$', 'backlog_ods'),
    (r'^(?P<project_id>\d+)/backlog/ods/states=(?P<states>\d+(:\d+)*)/$', 'backlog_ods'),
    (r'^(?P<project_id>\d+)/backlog/ods/states=(?P<states>\d+(:\d+)*)/suggest-(?P<suggest>actuals|estimates)/$', 'backlog_ods'),

    url(r'^(?P<project_id>\d+)/backlog/userstory/add/$', 'userstory_create', name="story_from_backlog"),
    url(r'^(?P<project_id>\d+)/backlog/save/$', 'backlog_save', name="backlog_save"),
    (r'^(?P<project_id>\d+)/backlog/archived/$', 'backlog_archived'),
    (r'^(?P<project_id>\d+)/backlog/archived/(?P<date>[0-9]{4}-[0-9]{2}-[0-9]{2})/$', 'backlog_archived'),

    url(r'^(?P<project_id>\d+)/release/add/$', 'release_create', name="release_create"),
    url(r'^(?P<project_id>\d+)/release/(?P<release_id>\d+)/edit/$', 'release_edit', name='release_edit'),
    (r'^(?P<project_id>\d+)/release/(?P<release_id>\d+)/delete/$', 'release_delete'),
    
    url(r'^(?P<project_id>\d+)/iteration/$', 'iteration_status', name="current_iteration_status"),
    url(r'^(?P<project_id>\d+)/iteration/(?P<iteration_id>\d+)/$', 'iteration_status', name="iteration_status_with_id"),
    url(r'^(?P<project_id>\d+)/iteration/import/$', 'iteration_import', name='iteration_import'),
    url(r'^(?P<project_id>\d+)/iteration/add/$', 'iteration_create', name="iteration_create"),
    url(r'^(?P<project_id>\d+)/iteration/(?P<iteration_id>\d+)/edit/$', 'iteration_edit', name='iteration_edit'),
    url(r'^(?P<project_id>\d+)/iteration/(?P<iteration_id>\d+)/delete/$', 'iteration_delete', name='iteration_delete'),

    url(r'^(?P<project_id>\d+)/taskboard/(?P<iteration_id>\d+)/$', 'taskboard', name="taskboard"),
    url(r'^(?P<project_id>\d+)/iteration/(?P<iteration_id>\d+)/userstory/add/$', 'userstory_create', name="story_from_iteration"),
    
    url(r'^(?P<project_id>\d+)/iteration/hours/$', 'iteration_hours', name="current_iteration_hours"),
    url(r'^(?P<project_id>\d+)/iteration/(?P<iteration_id>\d+)/hours/$', 'iteration_hours', name="iteration_hours_with_id"),
    (r'^(?P<project_id>\d+)/iteration/(?P<iteration_id>\d+)/hours_export/$', 'hours_export'),
    url(r'^(?P<project_id>\d+)/iteration/(?P<iteration_id>\d+)/cards/$', 'iteration_cards', name='iteration_cards'),
    (r'^(?P<project_id>\d+)/iteration/(?P<iteration_id>\d+)/status_table/$', 'iteration_status_table'),
    (r'^(?P<project_id>\d+)/iteration/(?P<iteration_id>\d+)/export/$', 'iteration_export'),
    (r'^(?P<project_id>\d+)/iteration/(?P<iteration_id>\d+)/burndown_chart/$', 'iteration_burndown_chart'),
    url(r'^(?P<project_id>\d+)/iteration/(?P<iteration_id>\d+)/impediment/add/$', 'impediment_create', name='impediment_create'),
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
    (r'^(?P<project_id>\d+)/userstory/(?P<userstory_id>\d+)/attachment/(?P<attachment_id>\d+)/view/$', 'view_attachment'),
    
    (r'^(?P<project_id>\d+)/userstory/(?P<userstory_id>\d+)/testcase/add/$', 'testcase_create'),
    (r'^(?P<project_id>\d+)/userstory/(?P<userstory_id>\d+)/testcase/(?P<testcase_id>\d+)/edit/$', 'testcase_edit'),
    (r'^(?P<project_id>\d+)/userstory/(?P<userstory_id>\d+)/testcase/(?P<testcase_id>\d+)/$', 'testcase_detail'),
    (r'^(?P<project_id>\d+)/userstory/(?P<userstory_id>\d+)/testcase/(?P<testcase_id>\d+)/delete/$', 'testcase_delete'),

    url(r'^(?P<project_id>\d+)/userstory/(?P<userstory_id>\d+)/testcase/(?P<testcase_id>\d+)/testresult/(?P<testresult_id>\d+)/$', 'testresult_detail', name='testresult_detail_with_id'),
    (r'^(?P<project_id>\d+)/userstory/(?P<userstory_id>\d+)/testcase/(?P<testcase_id>\d+)/testresult/add/$', 'testresult_create'),
    (r'^(?P<project_id>\d+)/userstory/(?P<userstory_id>\d+)/testcase/(?P<testcase_id>\d+)/testresult/(?P<testresult_id>\d+)/edit/$', 'testresult_edit'),
    (r'^(?P<project_id>\d+)/userstory/(?P<userstory_id>\d+)/testcase/(?P<testcase_id>\d+)/testresult/(?P<testresult_id>\d+)/delete/$', 'testresult_delete'),

    (r'^(?P<project_id>\d+)/search/', 'search'),
    url(r'^json/task/[ra]?(?P<task_id>\d+)/$', 'task_json', name="task_json"),

    url(r'^(?P<project_id>\d+)/log/$', 'timelog',name="timelog"),
    (r'^(?P<project_id>\d+)/log/task/(?P<task_id>\d+)/$', 'timelog_task'),

    (r'^close/$', 'close_window'),

    url(r'^csv/', 'csv_log_all_projects', name='timelogs_for_all_projects'),
    url(r'^(?P<project_id>\d+)/csv/(?P<username>[A-Za-z0-9_]+)/', 'csv_log', name='timelogs_for_user_in_project'),
    url(r'^(?P<project_id>\d+)/csv/', 'csv_log_for_project', name='timelogs_for_project'),

)

urlpatterns += patterns('',
#    (r'^admin/(.*)', admin.site.root),
#    (r'^agilito/(?P<path>.*)$', 'django.views.static.serve', {'document_root': media_root}),
    (r'^xmlrpc/', 'agilito.xmlrpc.xmlrpc.view', {'module':'agilito.xmlrpc'}),
#    (r'^(rsd.xml)$', 'django.views.static.serve', {'document_root': media_root}),

    (r'^feeds/(?P<url>.*)/$', 'agilito.feeds.feed', {'feed_dict': feeds}),
)

urlpatterns += patterns('agilito.threadedcommentsviews',
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
