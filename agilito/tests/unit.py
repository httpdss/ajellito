import datetime

from django import test

from agilito.models import User, UserStory, Task, TaskLog, Project, Iteration,\
    TestCase, TestResult
from agilito.forms import UserStoryForm, TestResultForm, TestCaseAddForm,\
    TestCaseEditForm, TaskForm
from django.template import loader, Context
from django import forms
from xml.dom import minidom

class QueryTestCase(test.TestCase):
    fixtures = ['database_dump.json']

    def test_query_user_story_name(self):
        """ 
        Simple tests just check if there exists a UserStory with a name
        containing the word 'owner'
        """
        query = "name:owner"
        self.assert_(len(UserStory.query(query)) > 0)
    
    def test_query_user_story_id(self):
        """
        Check if the US30 exists
        """
        query = "id:30"
        result = UserStory.query(query)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, 30)

    def test_query_task_name(self):
        """
        Simple test to check if the query function works with tasks
        """
        query = "name:coding"
        self.assert_(len(Task.query(query)) > 0)

class IterationStatusTestCase(test.TestCase):
    def setUp(self):
        super(IterationStatusTestCase, self).setUp()

        self.p1 = Project()
        self.p1.save()
        #self.i2 = Iteration(start_date=datetime.datetime.now(), end_date=datetime.datetime.now(), project=self.p1)
        #self.i2.save()

    def test_empty_case(self):
        it = Iteration(start_date=datetime.datetime.now(), end_date=datetime.datetime.now(), project=self.p1)
        it.save()
        self.assertEqual(it.us_accepted_percentage, 0)

    def test_start_case(self):
        it = Iteration(start_date=datetime.datetime.now(), end_date=datetime.datetime.now(), project=self.p1)
        it.save()
        us1 = UserStory(name='User story A', project=self.p1, iteration = it)
        us2 = UserStory(name='User story B', planned=10, project=self.p1, iteration = it)
        us3 = UserStory(name='User story C', planned=15, project=self.p1, iteration = it)
        us1.save()
        us2.save()
        us3.save()
        self.assertEqual(it.us_accepted_percentage, 0)

    def test_complete_case(self):
        it = Iteration(start_date=datetime.datetime.now(), end_date=datetime.datetime.now(), project=self.p1)
        it.save()
        us1 = UserStory(name='User story A', 
                    planned=10, state=40, project=self.p1, iteration = it)
        us2 = UserStory(name='User story B', 
                    planned=5, state=40, project=self.p1, iteration = it)
        us1.save()
        us2.save()
        self.assertEqual(it.us_accepted_percentage, 100)
        
    def test_parcial_case(self):
        it = Iteration(start_date=datetime.datetime.now(), end_date=datetime.datetime.now(), project=self.p1)
        it.save()
        us1 = UserStory(name='User story A', 
                    planned=45, state=20, project=self.p1, iteration = it)
        us2 = UserStory(name='User story B', 
                    planned=30, state=30, project=self.p1, iteration = it)
        us3 = UserStory(name='User story C', 
                    planned=25, state=40, project=self.p1, iteration = it)
        us1.save()
        us2.save()
        us3.save()
        self.assertEqual(it.us_accepted_percentage, 25)

class IterationStatusSummary(test.TestCase):
    def setUp(self):
        super(IterationStatusSummary, self).setUp()
        self.user1 = User(username='user1')
        self.user1.set_password('user1')
        self.user1.save()
        self.user2 = User(username='user2')
        self.user2.set_password('user2')
        self.user2.save()
        self.p1 = Project()
        self.p1.save()
        self.p1.project_members.add(self.user1)
        self.p1.project_members.add(self.user2)
        self.p1.save()
    
    def test_empty_case(self):
        it = Iteration(start_date=datetime.datetime.now(), end_date=datetime.datetime.now(), project=self.p1)
        it.save()
        self.assertEqual(it.estimated_without_owner, 0)
        self.assertEqual(it.user_estimated(self.user1.id), 0)
        self.assertEqual(it.user_progress(self.user1.id), 0)
        self.assertEqual(it.user_estimated(self.user2.id), 0)
        self.assertEqual(it.user_progress(self.user2.id), 0)
        self.assertEqual(it.users_total_status, 
            [{'name':self.user1.username,'progress':0, 'estimated':0},
             {'name':self.user2.username,'progress':0, 'estimated':0},
             {'name':'no owner','progress':'', 'estimated':0},
            ]        
        )

    def test_partial_case(self):
        it = Iteration(start_date=datetime.datetime.now(), end_date=datetime.datetime.now(), project=self.p1)
        it.save()
        us1 = UserStory(name='User story A', 
                    state=20, project=self.p1, iteration = it)
        us1.save()
        
        t1 = Task(name='Task 1 for US A', user_story = us1, owner= self.user1)
        t2 = Task(estimate=5, name='Task 2 for US A', user_story = us1, owner= self.user2)
        t3 = Task(estimate=10, name='Task 1 for US A', user_story = us1)
        for t in t1, t2, t3:
            t.save()



        tl1 = TaskLog(task=t1, summary="tasklog 1 for Task 1A", time_on_task=1, date=datetime.datetime.now(), owner=self.user1, iteration=it)
        tl2 = TaskLog(task=t2, summary="tasklog 2 for Task 2A", time_on_task=2, date=datetime.datetime.now(), 
owner=self.user1, iteration=it)
        for tl in tl1, tl2:
            tl.save()

        self.assertEqual(it.estimated_without_owner, 10)
        self.assertEqual(it.user_estimated(self.user1.id), 0)
        self.assertEqual(it.user_progress(self.user1.id), 3)
        self.assertEqual(it.user_estimated(self.user2.id), 5)
        self.assertEqual(it.user_progress(self.user2.id), 0)
        self.assertEqual(it.users_total_status, 
            [{'name':self.user1.username,'progress':3, 'estimated':0},
             {'name':self.user2.username,'progress':0, 'estimated':5},
             {'name':'no owner','progress':'', 'estimated':10},
            ]        
        )



    def test_complete_case(self):
        it = Iteration(start_date=datetime.datetime.now(), end_date=datetime.datetime.now(), project=self.p1)
        it.save()
        us1 = UserStory(name='User story A', 
                    planned=45, state=20, project=self.p1, iteration = it)
        us2 = UserStory(name='User story B', 
                    planned=30, state=30, project=self.p1, iteration = it)
        us1.save()
        us2.save()
        t1 = Task(estimate=10, name='Task 1 for US A', user_story = us1, owner= self.user1)
        t2 = Task(estimate=5, name='Task 2 for US A', user_story = us1, owner= self.user2)
        t3 = Task(estimate=1, name='Task 1 for US B', user_story = us2, owner= self.user1)
        t4 = Task(estimate=2, name='Task 2 for US B', user_story = us2, owner= self.user2)
        t5 = Task(estimate=5, name='Task 2 for US B', user_story = us2)
        t6 = Task(estimate=4, name='Task 2 for US B', user_story = us2)
        for t in t1, t2, t3, t4, t5, t6:
            t.save()
        tl1 = TaskLog(task=t1, summary="tasklog 1 for Task 1A", time_on_task=1, date=datetime.datetime.now(), owner=self.user1, iteration=it)
        tl2 = TaskLog(task=t2, summary="tasklog 2 for Task 2A", time_on_task=2, date=datetime.datetime.now(), owner=self.user1, iteration=it)
        tl3 = TaskLog(task=t3, summary="tasklog 1 for Task 1B", time_on_task=3, date=datetime.datetime.now(), owner=self.user2, iteration=it)
        tl4 = TaskLog(task=t4, summary="tasklog 2 for Task 2B", time_on_task=5, date=datetime.datetime.now(), owner=self.user2, iteration=it)        
        for tl in tl1, tl2, tl3, tl4:
            tl.save()

        self.assertEqual(it.estimated_without_owner, 9)
        self.assertEqual(it.user_estimated(self.user1.id), 11)
        self.assertEqual(it.user_estimated(self.user2.id), 7)
        self.assertEqual(it.user_progress(self.user1.id), 3)
        self.assertEqual(it.user_progress(self.user2.id), 8)
        self.assertEqual(it.users_total_status, 
            [{'name':self.user1.username,'progress':3, 'estimated':11},
             {'name':self.user2.username,'progress':8, 'estimated':7},
             {'name':'no owner','progress':'', 'estimated':9},
            ]        
        )


class UserStoryFormIterationFiltering(test.TestCase):


    def test_empty_case(self):
        p1 = Project()
        p1.save()
        usf = UserStoryForm(project=p1)
        itfield = usf.fields['iteration']
        choices = [c for c in itfield.choices]
        self.assertEqual(choices, [(u'', u'---------')])

    def test_full_case(self):
        p1 = Project()
        p1.save()
        it1 = Iteration(name='Iteration A', start_date=datetime.datetime.now(), end_date=datetime.datetime.now(), project = p1)
        it2 = Iteration(name='Iteration B', start_date=datetime.datetime.now(), end_date=datetime.datetime.now(), project = p1)
        it3 = Iteration(name='Iteration C', start_date=datetime.datetime.now(), end_date=datetime.datetime.now(), project = p1)
        for it in it1, it2, it3:        
            it.save()

        usf = UserStoryForm(project=p1)
        itfield = usf.fields['iteration']
        choices = [c for c in itfield.choices]
        echoices = [(u'', u'---------')]
        for it in it3, it2, it1:
            echoices += [(it.id,'IT%d: %s'%(it.id, it.name))]
        self.assertEqual(choices, echoices)


class GenericFormTest(test.TestCase):

    class TestForm(forms.Form):
        subject = forms.CharField(max_length=100)
        message = forms.CharField()
        sender = forms.EmailField()
        cc_myself = forms.BooleanField(required=False)

    def test_set_required(self):
        testform = self.TestForm()
        t = loader.get_template('generic_form.html')
        c = Context({ 'form': testform })
        rendered = t.render(c)
        dom = minidom.parseString(rendered)

        linodes = []
        for node in dom.childNodes[0].childNodes:
            if node.nodeType == 1:
                linodes.append(node.attributes['class'].value)
               
        self.assertEqual(linodes, [' required', ' required', ' required', ' '])

    def test_set_failed(self):
        testform = self.TestForm(data='')
        t = loader.get_template('generic_form.html')
        c = Context({ 'form': testform })
        rendered = t.render(c)
        dom = minidom.parseString(rendered)

        linodes = []
        ulnodes = []
        for node in dom.childNodes[0].childNodes:
            if node.nodeType == 1:
                linodes.append(node.attributes['class'].value)
                failed = False
                for child in node.childNodes:
                    if child.nodeType != 3 and child.nodeName == 'ul': 
                        failed = True
                ulnodes.append(failed)

        self.assertEqual(linodes, ['errors  required', 'errors  required', 'errors  required', ' '])
        self.assertEqual(ulnodes, [True, True, True, False])


class TestBurndown(test.TestCase):
    fixtures = ['burndown.json']

    def setUp(self):
        self.iter = Iteration.objects.all().get()
        self.task = Task.objects.all().get()

    def test_day_number_counts_from_start_of_day(self):
        self.assertEqual(self.iter.day_number(self.iter.start_date), 0)

    def test_day_number_counts_from_start_of_day_at_end_of_iteration_too(self):
        self.assertEqual(self.iter.day_number(self.iter.end_date + datetime.timedelta(10)), 10)

    def test_ideal_at_start_is_equal_to_estimates(self):
        self.assertEqual(self.iter.ideal_hours(self.iter.start_date),
                         self.iter.total_estimated())

    def test_ideal_after_end_is_equal_to_zero(self):
        after_end_date = self.iter.end_date + datetime.timedelta(1)
        self.assertEqual(self.iter.ideal_hours(after_end_date),
                         0)

    def test_remaining_initially_is_equal_to_estimate(self):
        self.assertEqual(self.task.remaining, self.task.estimate)

    def test_remaining_at_start_is_equal_to_estimate(self):
        self.assertEqual(self.task.remaining_for_date(self.iter.start_date),
                         self.task.estimate)

    def test_remaining_with_no_log_is_equal_to_original_estimate(self):
        self.assertEqual(self.task.remaining_for_date(self.iter.end_date),
                         self.task.estimate)

class TestEstimateTracking(test.TestCase):
    fixtures = ['burndown.json']

    def setUp(self):
        self.iter = Iteration.objects.all().get()
        self.task = Task.objects.all().get()
        self.old_remaining = self.task.remaining
        self.log = TaskLog(task=self.task,
                           time_on_task=1,
                           summary='...',
                           date=self.iter.start_date + datetime.timedelta(1),
                           owner=User.objects.all().get(),
                           old_remaining=self.old_remaining)
        self.task.remaining = self.task.remaining - self.log.time_on_task
        self.log.save()
        self.task.save()
        
    def test_remaining_after_log_is_equal_to_remaining(self):
        self.assertEqual(self.task.remaining_for_date(self.iter.end_date),
                         self.task.remaining or 0)

    def test_remaining_before_log_is_equal_to_estimate(self):
        self.assertEqual(self.task.remaining_for_date(self.iter.start_date),
                         self.task.estimate or 0)

        
    def test_burndown_data(self):
        bd = self.iter.burndown_data()
        # burndown data should be a list of dicts, for convenience
        self.assertEqual(bd[0],
                         dict(day=0,
                              remaining=self.task.estimate or 0,
                              ideal=self.task.estimate or 0))

    def test_burndown_data_too(self):
        bd = self.iter.burndown_data()
        # burndown data should be a list of dicts, for convenience
        self.assertEqual(bd[-1],
                         dict(day=10,
                              remaining=self.task.remaining or 0,
                              ideal=0))

    def test_burndown_shows_no_remaining_for_days_in_the_future(self):
        today = datetime.datetime.now().date()
        self.iter.start_date = today - datetime.timedelta(7)
        self.iter.end_date = today + datetime.timedelta(7)
        self.iter.save()

        self.assertEqual(self.iter.burndown_data()[-1]['remaining'], None)

class TestEstimateTrackingCopesWithNullEstimate(TestEstimateTracking):
    def setUp(self):
        super(TestEstimateTrackingCopesWithNullEstimate, self).setUp()
        self.log.old_remaining = None
        self.log.save()

class TestEstimateTrackingCopesWithNullEstimateAndOldRemaining(TestEstimateTracking):
    def setUp(self):
        super(TestEstimateTrackingCopesWithNullEstimateAndOldRemaining, self).setUp()
        self.log.old_remaining = None
        self.log.save()
        self.task.estimate = None
        self.task.save()

class TestEstimateTrackingCopesWithNullRemaining(TestEstimateTracking):
    def setUp(self):
        super(TestEstimateTrackingCopesWithNullRemaining, self).setUp()
        self.task.remaining = None
        self.task.save()

class TestTestResultForm(test.TestCase):
    fixtures = ['database_dump.json']

    def setUp(self):
      
        self.p1 = Project(name='Test Project 1')
        self.p2 = Project(name='Test Project 2')
        
        self.p1.save()
        self.p2.save()

        self.p1.project_members.add(User.objects.get(pk=1))
        self.p2.project_members.add(User.objects.get(pk=2))
        self.p2.project_members.add(User.objects.get(pk=3))
        
        self.us1 = UserStory(name='User story A', 
                    planned=45, state=20, project=self.p1)
        self.us2 = UserStory(name='User story B', 
                    planned=30, state=30, project=self.p2)
        
        self.us1.save()
        self.us2.save()

        self.tc1 = TestCase(user_story=self.us1, priority=10)
        self.tc2 = TestCase(user_story=self.us2, priority=10)
        self.tc3 = TestCase(user_story=self.us2, priority=10)

        self.tc1.save()
        self.tc2.save()
        self.tc3.save()

    def tearDown(self):
        for obj in self.tc1, self.tc2, self.tc3, self.us1, self.us2, self.p1, self.p2:
            obj.delete()

    def test_test_result_form_only_test_cases_of_current_project_simple(self):
        form = TestResultForm(project=self.p1)
        test_case_choices = list(form.fields['test_case'].choices)
        self.assertEqual(len(test_case_choices), 2)
        self.assertEqual(test_case_choices[1][1], unicode(self.tc1))
        tester_choices = list(form.fields['tester'].choices)
        self.assertEqual(len(tester_choices), 2)
        self.assertEqual(tester_choices[1][1], User.objects.get(pk=1).__str__())        


    def test_test_result_form_build_with_instance_has_only_test_cases_of_current_project(self):
        test_result = TestResult(result=10, test_case=self.tc1, tester=User.objects.all()[0])
        form = TestResultForm(project=self.p1,instance=test_result)
        test_case_choices = list(form.fields['test_case'].choices)
        self.assertEqual(len(test_case_choices), 2)
        self.assertEqual(test_case_choices[1][1], unicode(self.tc1))
        tester_choices = list(form.fields['tester'].choices)
        self.assertEqual(len(tester_choices), 2)
        self.assertEqual(tester_choices[1][1], User.objects.get(pk=1).__str__())        


    def test_test_result_form_only_test_cases_of_current_project_other(self):
        form = TestResultForm(project=self.p2)
        test_case_choices = list(form.fields['test_case'].choices)
        self.assertEqual(len(test_case_choices), 3)
        self.assert_(unicode(self.tc2) in set([test_case_choices[1][1], test_case_choices[2][1]]))
        tester_choices = list(form.fields['tester'].choices)
        self.assertEqual(len(tester_choices), 3)
        self.assertEqual(tester_choices[1][1], User.objects.get(pk=2).__str__())        


class TestTestCaseEditForm(test.TestCase):
    fixtures = ['database_dump.json']

    def setUp(self):
        self.p1 = Project(name='Test Project 1')
        self.p2 = Project(name='Test Project 2')
        
        self.p1.save()
        self.p2.save()
        
        self.us1 = UserStory(name='User story A', 
                    planned=45, state=20, project=self.p1)
        self.us2 = UserStory(name='User story B', 
                    planned=30, state=30, project=self.p2)
        self.us3 = UserStory(name='User story C', 
                    planned=30, state=30, project=self.p2)
        
        self.us1.save()
        self.us2.save()
        self.us3.save()

        self.tc1 = TestCase(user_story=self.us1, priority=10)
        self.tc2 = TestCase(user_story=self.us2, priority=10)

        self.tc1.save()
        self.tc2.save()


    def tearDown(self):
        for obj in self.tc1, self.tc2, self.us1, self.us2, self.p1, self.p2:
            obj.delete()

    def test_test_case_edit_form_has_current_project_us_only(self):
        form = TestCaseEditForm(project=self.tc1.user_story.project, instance=self.tc1)
        user_story_choices = list(form.fields['user_story'].choices)
        self.assertEqual(len(user_story_choices), 2)
        self.assertEqual(user_story_choices[1][1], unicode(self.us1))

    def test_test_case_edit_form_has_current_project_us_only_other(self):
        form = TestCaseEditForm(project=self.tc2.user_story.project, instance=self.tc2)
        user_story_choices = list(form.fields['user_story'].choices)
        self.assertEqual(len(user_story_choices), 3)
        self.assert_(unicode(self.us2) in set([user_story_choices[1][1], user_story_choices[2][1]]))
        self.assert_(unicode(self.us3) in set([user_story_choices[1][1], user_story_choices[2][1]]))

class TestTaskForm(test.TestCase):
    fixtures = ['database_dump.json']

    def setUp(self):
      
        self.p1 = Project(name='Test Project 1')
        self.p2 = Project(name='Test Project 2')
        
        self.p1.save()
        self.p2.save()

        self.p1.project_members.add(User.objects.get(pk=1))
        self.p2.project_members.add(User.objects.get(pk=2))
        self.p2.project_members.add(User.objects.get(pk=3))
        
        self.us1 = UserStory(name='User story A', 
                    planned=45, state=20, project=self.p1)
        self.us2 = UserStory(name='User story B', 
                    planned=30, state=30, project=self.p2)
        
        self.us1.save()
        self.us2.save()

    def tearDown(self):
    
        for obj in self.us1, self.us2, self.p1, self.p2:
            obj.delete()

    def test_task_form_has_only_relevant_owners_simple(self):
        form = TaskForm(project=self.p1)
        owner_choices = list(form.fields['owner'].choices)
        self.assertEqual(len(owner_choices), 2)
        self.assertEqual(owner_choices[1][1], User.objects.get(pk=1).__str__())

    def test_task_form_has_only_relevant_owners_w_instance_simple(self):
        t1 = Task(name='Task 1 for US A', user_story = self.us1, owner=User.objects.get(pk=2))
        form = TaskForm(project=self.p2, instance=t1)
        owner_choices = list(form.fields['owner'].choices)
        self.assertEqual(len(owner_choices), 3)
        self.assertEqual(owner_choices[1][1], User.objects.get(pk=2).__str__())
        self.assertEqual(owner_choices[2][1], User.objects.get(pk=3).__str__())


