from django.conf import settings
from django.db.models import signals
from django.utils.translation import ugettext_noop as _

if "notification" in settings.INSTALLED_APPS:
    from notification import models as notification

    def create_notice_types(app, created_models, verbosity, **kwargs):
        notification.create_notice_type("agilito_task_create", _("Task Added"), _("a task has been added"), default=0)
        notification.create_notice_type("agilito_task_edit", _("Task Edited"), _("a task has been edited"), default=0)
        notification.create_notice_type("agilito_task_delete", _("Task Edited"), _("a task has been edited"), default=0)

        notification.create_notice_type("agilito_comment_create", _("Comment Added"), _("a comment has been added"), default=0)
        notification.create_notice_type("agilito_comment_delete", _("Comment Deleted"), _("a comment has been deleted"), default=0)

        notification.create_notice_type("agilito_user_story_create", _("User Story Added"), _("an user story has been added"), default=0)
        notification.create_notice_type("agilito_user_story_edit", _("User Story Edited"), _("an user story has been edited"), default=0)
        notification.create_notice_type("agilito_user_story_delete", _("User Story Deleted"), _("an user story has been deleted"), default=0)

        notification.create_notice_type("agilito_iteration_create", _("Iteration Added"), _("an iteration has been added"), default=0)
        notification.create_notice_type("agilito_iteration_edit", _("Iteration Edited"), _("an iteration has been edited"), default=0)
        notification.create_notice_type("agilito_iteration_delete", _("Iteration Deleted"), _("an iteration has been deleted"), default=0)

        notification.create_notice_type("agilito_impediment_create", _("Impediment Added"), _("an impediment has been added"), default=0)
        notification.create_notice_type("agilito_impediment_edit", _("Impediment Edited"), _("an impediment has been edited"), default=0)
        notification.create_notice_type("agilito_impediment_delete", _("Impediment Deleted"), _("an impediment has been deleted"), default=0)

        notification.create_notice_type("agilito_attachment_create", _("Attachment Added"), _("an attachment has been added"), default=0)
        notification.create_notice_type("agilito_attachment_edit", _("Attachment Edited"), _("an attachment has been edited"), default=0)
        notification.create_notice_type("agilito_attachment_delete", _("Attachment Deleted"), _("an attachment has been deleted"), default=0)

        notification.create_notice_type("agilito_user_story_move", _("User Story Moved"), _("an user story has been moved"), default=0)

        notification.create_notice_type("agilito_testcase_create", _("Test Case Added"), _("a test case has been added"), default=0)
        notification.create_notice_type("agilito_testcase_edit", _("Test Case Edited"), _("a test case has been edited"), default=0)
        notification.create_notice_type("agilito_testcase_delete", _("Test Case Deleted"), _("a test case has been deleted"), default=0)

        notification.create_notice_type("agilito_testresult_create", _("Test Result Added"), _("a test result has been added"), default=0)
        notification.create_notice_type("agilito_testresult_edit", _("Test Result Edited"), _("a test result has been edited"), default=0)
        notification.create_notice_type("agilito_testresult_delete", _("Test Result Deleted"), _("a test result has been deleted"), default=0)

        notification.create_notice_type("agilito_backlog_save", _("Backlog saved"), _("backlog has been saved"), default=0)
        notification.create_notice_type("agilito_timelog_alert", _("Log alert"), _("you need to log your hours"), default=0)

    signals.post_syncdb.connect(create_notice_types, sender=notification)
else:
    print "Skipping creation of NoticeTypes as notification app not found"
