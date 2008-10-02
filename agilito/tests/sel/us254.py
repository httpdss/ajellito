from us49 import TestUS49Base
from agilito.models import UserStory, Task, TaskLog 
from base import BASE_URL
from datetime import datetime

class TestUS254(TestUS49Base):

    def setUp(self):
        super(TestUS254, self).setUp()

        self.user_story_states = dict((v,k) for (k,v) in UserStory.STATES)

        self.story_2 = UserStory(name='TestUS254 A', project=self.project,
                               description='a userstory to test us254',
                               iteration=self.iteration, planned=42, rank=1,
                               state=10, blocked=False)
        self.story_2.save()

        self.story_3 = UserStory(name='TestUS254 B', project=self.project,
                               description='another userstory to test us254',
                               iteration=self.iteration, planned=42, rank=1,
                               state=10, blocked=False)
        self.story_3.save()

        self.story_4 = UserStory(name='TestUS254 C', project=self.project,
                               description='yet another userstory to test us254',
                               iteration=self.iteration, planned=42, rank=1,
                               state=10, blocked=False)
        self.story_4.save()

        self.story_5 = UserStory(name='TestUS254 D', project=self.project,
                               description='again, yet another userstory to test us254',
                               iteration=self.iteration, planned=42, rank=1,
                               state=10, blocked=False)
        self.story_5.save()

        
        self.task_states = dict((v,k) for (k,v) in Task.STATES)

        # actuals > 0, not completed -> change state to In progress

        self.task_c = Task(name="Task C", estimate=8, remaining=6,
                           state=self.task_states['Defined'],
                           owner=self.user, user_story=self.story_2)
        self.task_c.save()

        self.tasklog_c = TaskLog(task=self.task_c, time_on_task=2, summary='test',
                                 date=datetime.today(), owner=self.user,
                                 old_remaining=0)

        self.tasklog_c.save()

        # actuals > 0, completed, remaining > 0, all task in us completed -> 
        # should change US to complete and change task to complete, remaining 0

        self.task_d = Task(name="Task D", estimate=2, remaining=2,
                           state=self.task_states['Complete'],
                           owner=self.user, user_story=self.story_3)
        self.task_d.save()

        self.task_f = Task(name="Task F", estimate=2, remaining=0,
                           state=self.task_states['Complete'],
                           owner=self.user, user_story=self.story_3)
        self.task_f.save()

        self.tasklog_f = TaskLog(task=self.task_f, time_on_task=2, summary='test',
                                 date=datetime.today(), owner=self.user,
                                 old_remaining=0)

        self.tasklog_f.save()

        self.tasklog_d = TaskLog(task=self.task_d, time_on_task=2, summary='test',
                                 date=datetime.today(), owner=self.user,
                                 old_remaining=0)

        self.tasklog_d.save()


        # actuals > 0, defined, remaining = 0, not all task in us completed 
        # should change to complete.                           
        self.task_e = Task(name="Task E", estimate=2, remaining=0,
                           state=self.task_states['Defined'],
                           owner=self.user, user_story=self.story_2)
        self.task_e.save()

        self.tasklog_e = TaskLog(task=self.task_e, time_on_task=2, summary='test',
                                 date=datetime.today(), owner=self.user,
                                 old_remaining=0)

        self.tasklog_e.save()

        # actuals > 0, in progress, remaining = 0, not all task in us completed 
        # should change to complete.   
        self.task_g = Task(name="Task G", estimate=2, remaining=0,
                           state=self.task_states['In Progress'],
                           owner=self.user, user_story=self.story_2)
        self.task_g.save()

        self.tasklog_g = TaskLog(task=self.task_g, time_on_task=2, summary='test',
                                 date=datetime.today(), owner=self.user,
                                 old_remaining=0)

        self.tasklog_g.save()



    def tearDown(self):
        super(TestUS254, self).tearDown()
        for obj in self.tasklog_f, self.tasklog_e, self.tasklog_d, self.tasklog_c,\
            self.task_g, self.task_f, self.task_e, self.task_d, self.task_c,\
            self.story_5, self.story_4, self.story_3, self.story_2:
            obj.delete() 

    def test_adding_a_task_in_progress_changes_us_to_in_progress(self):
        b = self.browser
        b.click("link=Iteration")
        b.wait()

        b.click("link=TestUS254 D")
        b.wait()        

        b.click("link=add a task")
        b.wait()

        b.type("id_name", "A sample detailed task")
        b.type("id_description", "This is a detailed task")
        b.type("id_estimate", "10")
        b.type("id_remaining", "10")
        b.type("id_state", "20")
        b.click("xpath=id('content')/form/input")
        b.wait()

        obj = UserStory.objects.get(id=self.story_5.id)
        self.assertEqual(obj.state, 20)

    def test_adding_a_task_in_progress_and_one_task_complete_changes_us_to_in_progress(self):
        b = self.browser
        b.click("link=Iteration")
        b.wait()

        b.click("link=TestUS254 D")
        b.wait()        
        last_location = b.get_location()

        b.click("link=add a task")
        b.wait()

        b.type("id_name", "A sample detailed task")
        b.type("id_description", "This is a detailed task")
        b.type("id_estimate", "10")
        b.type("id_remaining", "10")
        b.type("id_state", "20")
        b.click("xpath=id('content')/form/input")
        b.wait()

        obj = UserStory.objects.get(id=self.story_5.id)
        self.assertEqual(obj.state, 20)
        self.assertEqual(last_location, b.get_location())

        b.click("link=add a task")
        b.wait()

        b.type("id_name", "A sample detailed task")
        b.type("id_description", "This is a detailed task")
        b.type("id_estimate", "10")
        b.type("id_remaining", "0")
        b.type("id_state", "30")
        b.click("xpath=id('content')/form/input")
        b.wait()

        obj = UserStory.objects.get(id=self.story_5.id)
        self.assertEqual(obj.state, 20)

 
    def test_adding_a_task_define_does_not_change_state_of_us(self):
        b = self.browser
        b.click("link=Iteration")
        b.wait()

        b.click("link=TestUS254 D")
        b.wait()        

        b.click("link=add a task")
        b.wait()

        b.type("id_name", "A sample detailed task")
        b.type("id_description", "This is a detailed task")
        b.type("id_estimate", "10")
        b.type("id_remaining", "10")
        b.type("id_state", "10")
        b.click("xpath=id('content')/form/input")
        b.wait()

        obj = UserStory.objects.get(id=self.story_5.id)
        self.assertEqual(obj.state, 10)

    def test_editing_task_with_actuals_sets_from_defined_to_complete(self):
        # Task has actuals > 0 is on state defined should change state to 'In Progress'
        # Should change story to 'In Progress'

        b = self.browser
        b.click("link=Iteration")
        b.wait()

        b.click("link=TestUS254 A")
        b.wait()        

        b.click("xpath=id('task_edit_%d')/img" % self.task_c.id)
        b.wait()

        b.click("xpath=id('content')/form/input")
        b.wait()

        # Reload obj task, self.task_c is on a stale state:
        obj = Task.objects.get(id=self.task_c.id)
        # Check that only that the state changed
        self.assertEqual(obj.name, "Task C")
        self.assertEqual(obj.description, '')
        self.assertEqual(obj.estimate, 8)
        self.assertEqual(obj.remaining, 6)
        self.assertEqual(obj.owner, self.user)
        self.assertEqual(obj.user_story, self.story_2)
        self.assertEqual(obj.state, self.task_states['In Progress'])  
        self.assertEqual(obj.user_story.state, self.user_story_states['In Progress'])

    def test_editing_task_with_actuals_and_in_complete_state_sets_remaining_to_zero(self):
        # Task has actuals > 0, is completed, and has remaining > 0. 
        # All task in us completed. (There are two) 
        # should change US to complete and change task to complete, remaining 0
        
        b = self.browser
        b.click("link=Iteration")
        b.wait()

        b.click("link=TestUS254 B")
        b.wait()        

        b.click("xpath=id('task_edit_%d')/img" % self.task_d.id)
        b.wait()

        b.click("xpath=id('content')/form/input")
        b.wait()

        # Reload obj task, self.task_c is on a stale state:
        obj = Task.objects.get(id=self.task_d.id)
        # Check that nothing else changed except that which should
        self.assertEqual(obj.name, "Task D")
        self.assertEqual(obj.description, '')
        self.assertEqual(obj.estimate, 2)
        self.assertEqual(obj.remaining, 0)
        self.assertEqual(obj.owner, self.user)
        self.assertEqual(obj.user_story, self.story_3)
        self.assertEqual(obj.state, self.task_states['Complete'])  
        self.assertEqual(obj.user_story.state, self.user_story_states['Completed'])

    def test_editing_task_with_actuals_remaining_on_zero_in_defined_state_sets_state_to_complete(self):
        # Task has actuals > 0, is defined, and has remaining = 0. 
        # Not all task in us completed.
        # Should change US to In Progress and change task to complete, remaining 0

        
        b = self.browser
        b.click("link=Iteration")
        b.wait()

        b.click("link=TestUS254 A")
        b.wait()        

        b.click("xpath=id('task_edit_%d')/img" % self.task_e.id)
        b.wait()

        b.click("xpath=id('content')/form/input")
        b.wait()

        # Reload obj task, self.task_c is on a stale state:
        obj = Task.objects.get(id=self.task_e.id)
        # Check that nothing else changed except that which should
        self.assertEqual(obj.name, "Task E")
        self.assertEqual(obj.description, '')
        self.assertEqual(obj.estimate, 2)
        self.assertEqual(obj.remaining, 0)
        self.assertEqual(obj.owner, self.user)
        self.assertEqual(obj.user_story, self.story_2)
        self.assertEqual(obj.state, self.task_states['Complete'])  
        self.assertEqual(obj.user_story.state, self.user_story_states['In Progress'])

    def test_editing_task_with_actuals_remaining_on_zero_in_in_progress_state_sets_state_to_complete(self):
        # Task has actuals > 0, is in progress, and has remaining = 0. 
        # Not all task in us completed.
        # Should change US to In Progress and change task to complete, remaining 0
        
        b = self.browser
        b.click("link=Iteration")
        b.wait()

        b.click("link=TestUS254 A")
        b.wait()        

        b.click("xpath=id('task_edit_%d')/img" % self.task_g.id)
        b.wait()

        b.click("xpath=id('content')/form/input")
        b.wait()

        # Reload obj task, self.task_c is on a stale state:
        obj = Task.objects.get(id=self.task_g.id)
        # Check that nothing else changed except that which should
        self.assertEqual(obj.name, "Task G")
        self.assertEqual(obj.description, '')
        self.assertEqual(obj.estimate, 2)
        self.assertEqual(obj.remaining, 0)
        self.assertEqual(obj.owner, self.user)
        self.assertEqual(obj.user_story, self.story_2)
        self.assertEqual(obj.state, self.task_states['Complete'])  
        self.assertEqual(obj.user_story.state, self.user_story_states['In Progress'])

