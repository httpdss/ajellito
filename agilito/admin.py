from agilito.models import Project, Release, Iteration, UserStoryAttachment,\
    UserStory, UserProfile, Task, TestCase, TestResult, TaskLog, \
    Impediment
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

class ImpedimentInLine(admin.TabularInline):
    model = Impediment
    extra = 1

class ProjectAdmin(admin.ModelAdmin):
    filter_horizontal = ('project_members',)

class ReleaseAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'project')
    list_filter = ('project',)
    ordering = ('project',)
    search_fields = ['name', 'description', 'project__name']

class IterationAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'project', 'start_date', 'end_date')
    list_filter = ('project',)
    date_hierarchy = 'start_date'
    ordering = ('project',)
    search_fields = ['name', 'description', 'project__name']

class UserProfileAdmin(admin.ModelAdmin):
    pass

class UserStoryAttachmentAdmin(admin.ModelAdmin):
    list_display = ('name',)
    list_display_links = ('name',)    

class UserStoryAdmin(admin.ModelAdmin):
    inlines = [UserStoryAttachmentInLine, TestCaseInLine, TaskInLine]
    list_display = ('id', 'name', 'rank', 'planned', 'iteration', 'state',
                    'estimated', 'actuals', 'remaining')
    list_display_links = ('id', 'name',)
    list_filter = ('project', 'iteration', 'state', )
    ordering = ('rank','planned', )
    search_fields = ['name', 'description']

    fieldsets = ((None, {'fields': ('name', 'description',
                                   ('project', 'iteration'),
                                   ('rank', 'state', 'planned', ))}), )

class TaskAdmin(admin.ModelAdmin):
    inlines = [ImpedimentInLine]
    list_display = ('name', 'estimate', 'actuals', 'remaining', 
                    'state', 'category', 'owner', 'user_story')
    list_display_links = ('name', 'owner', 'user_story')
    fieldsets = ((None, { 'fields': ('name', 'description', 'user_story',
                                    ('estimate', 'remaining', 'state', 'category'),
                                     'owner')}),)
    search_fields = ('name', 'description', 'user_story__name')

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
    search_fields = ('name', 'description', 'user_story__name')

class TestResultAdmin(admin.ModelAdmin):
    list_display = ('test_case', 'date', 'tester', 'result')
    list_display_links = ('test_case', 'tester')
    list_filter = ('result', 'tester')

class TaskLogAdmin(admin.ModelAdmin):
    list_display = ('summary', 'task', 'iteration', 'project', 'date', 'time_on_task', 'owner')
    list_filter = ('owner',)
    date_hierarchy = 'date'
    search_fields = ('summary', 'iteration__name', 'iteration__project__name')
    ordering = ('-date',)

class ImpedimentAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'opened', 'resolved', 'tasks')
    ordering = ('-opened',)

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
#admin.site.register(Impediment, ImpedimentAdmin)
