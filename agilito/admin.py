from agilito.models import Project, Release, Iteration, UserStoryAttachment,\
    UserStory, UserProfile, Task, TestCase, TestResult, TaskLog, \
    Impediment, ProjectMember
from django.contrib import admin
from django import forms
from django.shortcuts import render_to_response
from tagging.models import Tag


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

class ProjectMemberInLine(admin.TabularInline):
    model = ProjectMember
    extra = 1
        
class ProjectAdmin(admin.ModelAdmin):
    inlines = [ProjectMemberInLine]

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
    list_display = ('id', 'name', 'task_count', 'estimated', 'actuals', 'remaining',
                    'iteration', 'state', 'rank', 'size')
    list_display_links = ('id', 'name',)
    list_filter = ('project', 'iteration', 'state', )
    ordering = ('rank','size', )
    search_fields = ['name', 'description']
    
    fieldsets = ((None, {'fields': ('name', 'description',
                                   ('project', 'iteration'),
                                   ('rank', 'state', 'size', ))}), )

class TaskAdmin(admin.ModelAdmin):
    list_display = ('name', 'estimate', 'actuals', 'remaining',
                    'state', 'category', 'owner', 'user_story')
    list_display_links = ('name', 'owner', 'user_story')
    list_filter = ('owner', 'state', 'user_story__iteration__name')
    fieldsets = ((None, { 'fields': ('name', 'description', 'user_story',
                                    ('estimate', 'remaining', 'state', 'category'),
                                     'owner')}),)
    search_fields = ('name', 'description', 'user_story__name')
    
    actions = ['add_tag']

    class AddTagForm(forms.Form):
        _selected_action = forms.CharField(widget=forms.MultipleHiddenInput)
        tag = forms.ModelChoiceField(Tag.objects)

    def add_tag(self, request, queryset):
        form = None

        if 'apply' in request.POST:
            form = self.AddTagForm(request.POST)

            if form.is_valid():
                tag = form.cleaned_data['tag']

                count = 0
                for task in queryset:
                    task.tags.add(tag)
                    count += 1

                plural = ''
                if count != 1:
                    plural = 's'

                self.message_user(request, "Successfully added tag %s to %d task%s." % (tag, count, plural))
                return HttpResponseRedirect(request.get_full_path())

        if not form:
            form = self.AddTagForm(initial={'_selected_action': request.POST.getlist(admin.ACTION_CHECKBOX_NAME)})

        return render_to_response('admin/add_tag.html', {'tasks': queryset,
                                                         'tag_form': form,
                                                        })
    add_tag.short_description = "Add tag to task"
    

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
    list_filter = ('owner','date')
    date_hierarchy = 'date'
    search_fields = ('summary', 'iteration__name', 'iteration__project__name')
    ordering = ('-date',)

class ImpedimentAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'opened', 'resolved')
    ordering = ('-opened',)
    
class ProjectMemberAdmin(admin.ModelAdmin):
    list_display = ('user','project','role')
    list_filter = ('project','role')
    search_fields = ['member__username']
    list_editable = ('role',)
    

admin.site.register(ProjectMember, ProjectMemberAdmin)
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
admin.site.register(Impediment, ImpedimentAdmin)