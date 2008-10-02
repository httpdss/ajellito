from agilito.models import Project, Release, Iteration, UserStoryAttachment,\
    UserStory, UserProfile, Task, TestCase, TestResult, TaskLog
from django.contrib import admin

#
# In Lines
#
class UserStoryAttachmentInLine(admin.TabularInline):
    model = UserStoryAttachment
    extra = 1

class TestCaseInLine(admin.TabularInline):
    model = TestCase
    extra = 1

class TaskInLine(admin.TabularInline):
    model = Task
    extra = 1

class ProjectAdmin(admin.ModelAdmin):
    filter_horizontal = ('project_members',)

class ReleaseAdmin(admin.ModelAdmin):
    pass

class IterationAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_date', 'end_date')

class UserProfileAdmin(admin.ModelAdmin):
    pass

class UserStoryAttachmentAdmin(admin.ModelAdmin):
    list_display = ('name',)
    list_display_links = ('name',)    

class UserStoryAdmin(admin.ModelAdmin):
    inlines = [UserStoryAttachmentInLine, TestCaseInLine, TaskInLine]
    list_display = ('id', 'name', 'rank', 'planned', 'iteration', 'state',
                    'blocked', 'estimated', 'actuals', 'remaining')
    list_display_links = ('id', 'name',)
    list_filter = ('iteration', 'state', 'blocked',)
    ordering = ('rank','planned', 'blocked',)
    search_fields = ['name', 'description']

    fieldsets = ((None, {'fields': ('name', 'description',
                                   ('project', 'iteration'),
                                   ('rank', 'state', 'planned', 'blocked'))}), )

class TaskAdmin(admin.ModelAdmin):
    list_display = ('name', 'estimate', 'actuals', 'remaining', 
                    'state', 'category', 'owner', 'user_story')
    list_display_links = ('name', 'owner', 'user_story')
    fieldsets = ((None, { 'fields': ('name', 'description', 'user_story',
                                    ('estimate', 'remaining', 'state', 'category'),
                                     'owner')}),)


class TestCaseAdmin(admin.ModelAdmin):
    fieldsets = ((None, {
                'fields': ('name', 'description', 'user_story'),
                }),
                ('Advanced', {
                'classes': 'collapse',
                'fields': ('priority', 'precondition', 'steps', 
                            'postcondition',),
                }),
                )

    list_display = ('id', 'name', 'user_story', 'priority')
    list_display_links = ('id', 'name',)
    list_filter = ('priority',)

class TestResultAdmin(admin.ModelAdmin):
    list_display = ('test_case', 'date', 'tester', 'result')
    list_display_links = ('test_case', 'tester')
    list_filter = ('result', 'tester')

class TaskLogAdmin(admin.ModelAdmin):
    list_display = ('summary', 'iteration', 'task', 'date', 'time_on_task', 'owner')
    list_filter = ('task', 'iteration', 'owner')
    date_hierarchy = 'date'

admin.site.register(Project, ProjectAdmin)
admin.site.register(Release, ReleaseAdmin)
admin.site.register(Iteration, IterationAdmin)
admin.site.register(UserStoryAttachment, UserStoryAttachmentAdmin)
admin.site.register(UserStory, UserStoryAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(Task, TaskAdmin)
admin.site.register(TestCase, TestCaseAdmin)
admin.site.register(TestResult, TestResultAdmin)
admin.site.register(TaskLog, TaskLogAdmin)
