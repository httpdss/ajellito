import os
from django.conf.urls.defaults import *
from django.contrib import admin
from django.contrib.auth.decorators import login_required

from agilito.feeds import BacklogFeed, IterationFeed, NoticeFeed

from tastypie.api import Api
from agilito.api import ProjectResource

from agilito.views import ProjectList, ProjectCreate, ProjectDetail, FileList

admin.autodiscover()

media_root = os.path.join(os.path.dirname(__file__), 'media')

feeds = {
    'backlog': BacklogFeed,
    'iteration': IterationFeed,
    'notice': NoticeFeed,
    }

v1_api = Api(api_name='v1')
v1_api.register(ProjectResource())

urlpatterns = patterns('agilito.views',
    url(r'^$', 'index', name="agilito_index"),

    url(r"^api/", include(v1_api.urls)),

    url(r"^project/$", login_required(ProjectList.as_view()), name="project_list"),
    url(r"^project/create/$",  login_required(ProjectCreate.as_view()), name="project_create"),
    url(r"^project/(?P<pk>\d+)/$", login_required(ProjectDetail.as_view()), name="project_detail"),

    # url(r'^(?P<project_id>\d+)/testcase/$', login_required(TestCaseList.as_view()), name="testcase_list"),
    #     url(r'^(?P<project_id>\d+)/testcase/(?P<iteration_id>\d+)/$', login_required(TestCaseList.as_view()), name="iteration_hours_with_id"),

    url(r'^(?P<project_id>\d+)/backlog/$', 'backlog', name='product_backlog'),
    url(r'^(?P<project_id>\d+)/files/$', login_required(FileList.as_view()), name='agilito_project_files'),
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
    url(r'^(?P<project_id>\d+)/iteration/hours/(?P<username>[A-Za-z0-9_\.]+)/$', 'iteration_daily_hours', name="current_daily_hours"),
    url(r'^(?P<project_id>\d+)/iteration/(?P<iteration_id>\d+)/hours/(?P<username>[A-Za-z0-9_\.]+)/$', 'iteration_daily_hours', name="current_daily_hours_with_id"),
    url(r'^(?P<project_id>\d+)/iteration/(?P<iteration_id>\d+)/hours/$', 'iteration_hours', name="iteration_hours_with_id"),
    (r'^(?P<project_id>\d+)/iteration/(?P<iteration_id>\d+)/hours_export/$', 'hours_export'),
    url(r'^(?P<project_id>\d+)/iteration/(?P<iteration_id>\d+)/cards/$', 'iteration_cards', name='iteration_cards'),
    (r'^(?P<project_id>\d+)/iteration/(?P<iteration_id>\d+)/status_table/$', 'iteration_status_table'),
    (r'^(?P<project_id>\d+)/iteration/(?P<iteration_id>\d+)/export/$', 'iteration_export'),
    (r'^(?P<project_id>\d+)/iteration/(?P<iteration_id>\d+)/burndown_chart/$', 'iteration_burndown_chart'),
    url(r'^(?P<project_id>\d+)/iteration/(?P<iteration_id>\d+)/impediment/add/$', 'impediment_create', name='impediment_create'),
    url(r'^(?P<project_id>\d+)/iteration/(?P<iteration_id>\d+)/impediment/(?P<impediment_id>\d+)/edit/$', 'impediment_edit', name='impediment_edit'),
    (r'^(?P<project_id>\d+)/product_backlog_chart/(?P<iteration_id>.*)$', 'product_backlog_chart'),

    url(r'^(?P<project_id>\d+)/userstory/(?P<userstory_id>\d+)/$', 'userstory_detail', name='agilito_userstory_detail'),
    url(r'^(?P<project_id>\d+)/userstory/(?P<userstory_id>\d+)/delete/$', 'userstory_delete', name="agilito_userstory_delete"),
    url(r'^(?P<project_id>\d+)/userstory/(?P<userstory_id>\d+)/edit/$', 'userstory_edit', name="agilito_userstory_edit"),
    (r'^(?P<project_id>\d+)/userstory/(?P<userstory_id>\d+)/move/$', 'userstory_move'),

    url(r'^(?P<project_id>\d+)/userstory/(?P<userstory_id>\d+)/task/add/$', 'task_create', name="agilito_task_create"),
    url(r'^(?P<project_id>\d+)/userstory/(?P<userstory_id>\d+)/task/(?P<task_id>\d+)/edit/$', 'task_edit', name="agilito_task_edit"),
    url(r'^(?P<project_id>\d+)/userstory/(?P<userstory_id>\d+)/task/(?P<task_id>\d+)/$', 'task_detail', name="agilito_task_detail"),
    (r'^(?P<project_id>\d+)/userstory/(?P<userstory_id>\d+)/task/(?P<task_id>\d+)/delete/$', 'task_delete'),


    url(r'^(?P<project_id>\d+)/userstory/(?P<userstory_id>\d+)/attachment/add/$', 'add_attachment', name="agilito_add_attachment"),
    #just left it for the record.
    #(r'^(?P<project_id>\d+)/userstory/(?P<userstory_id>\d+)/attachment/(?P<attachment_id>\d+)/edit/$', 'edit_attachment'),
    (r'^(?P<project_id>\d+)/userstory/(?P<userstory_id>\d+)/attachment/(?P<attachment_id>\d+)/delete/$', 'delete_attachment'),
    url(r'^(?P<project_id>\d+)/userstory/(?P<userstory_id>\d+)/attachment/(?P<attachment_id>\d+)/view/$', 'view_attachment', name="agilito_view_attachment"),
    url(r'^(?P<project_id>\d+)/userstory/(?P<userstory_id>\d+)/attachment/(?P<attachment_id>\d+)/view/(?P<secret>[A-Za-z0-9_]*)/$', 'view_attachment', name="agilito_view_attachment_secret"),

    url(r'^(?P<project_id>\d+)/userstory/(?P<userstory_id>\d+)/testcase/add/$', 'testcase_create', name="agilito_testcase_create"),
    (r'^(?P<project_id>\d+)/userstory/(?P<userstory_id>\d+)/testcase/(?P<testcase_id>\d+)/edit/$', 'testcase_edit'),
    (r'^(?P<project_id>\d+)/userstory/(?P<userstory_id>\d+)/testcase/(?P<testcase_id>\d+)/$', 'testcase_detail'),
    (r'^(?P<project_id>\d+)/userstory/(?P<userstory_id>\d+)/testcase/(?P<testcase_id>\d+)/delete/$', 'testcase_delete'),

    url(r'^(?P<project_id>\d+)/userstory/(?P<userstory_id>\d+)/testcase/(?P<testcase_id>\d+)/testresult/(?P<testresult_id>\d+)/$', 'testresult_detail', name='testresult_detail_with_id'),
    (r'^(?P<project_id>\d+)/userstory/(?P<userstory_id>\d+)/testcase/(?P<testcase_id>\d+)/testresult/add/$', 'testresult_create'),
    (r'^(?P<project_id>\d+)/userstory/(?P<userstory_id>\d+)/testcase/(?P<testcase_id>\d+)/testresult/(?P<testresult_id>\d+)/edit/$', 'testresult_edit'),
    (r'^(?P<project_id>\d+)/userstory/(?P<userstory_id>\d+)/testcase/(?P<testcase_id>\d+)/testresult/(?P<testresult_id>\d+)/delete/$', 'testresult_delete'),

    url(r'^(?P<project_id>\d+)/search/', 'search', name="agilito_search"),
    url(r'^json/task/[ra]?(?P<task_id>\d+)/$', 'task_json', name="task_json"),

    url(r'^(?P<project_id>\d+)/log/$', 'timelog', name="timelog"),
    url(r'^(?P<project_id>\d+)/log_alert/$', 'timelog_alert', name="timelog_alert"),
    url(r'^(?P<project_id>\d+)/mylog/$', 'timelog_mylog', name="agilito_tasklog_mylog"),
    (r'^(?P<project_id>\d+)/log/task/(?P<task_id>\d+)/$', 'timelog_task'),

    url(r'^csv/', 'csv_log_all_projects', name='timelogs_for_all_projects'),
    url(r'^(?P<project_id>\d+)/csv/(?P<username>[A-Za-z0-9_\.]+)/', 'csv_log', name='timelogs_for_user_in_project'),
    url(r'^(?P<project_id>\d+)/csv/', 'csv_log_for_project', name='timelogs_for_project'),

)

urlpatterns += patterns('',
#    (r'^agilito/(?P<path>.*)$', 'django.views.static.serve', {'document_root': media_root}),
#    (r'^xmlrpc/', 'agilito.xmlrpc.xmlrpc.view', {'module':'agilito.xmlrpc'}),
#    (r'^(rsd.xml)$', 'django.views.static.serve', {'document_root': media_root}),
    (r'^(?P<project_id>\d+)/touch/$', 'agilito.tools.touch_cache'),
    (r'^feeds/(?P<url>.*)/$', 'agilito.feeds.feed', {'feed_dict': feeds}),
)
