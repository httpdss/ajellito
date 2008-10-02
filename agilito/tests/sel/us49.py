from base import SeleniumBase
from agilito.models import Project, User, UserStory, Task, Iteration

class TestUS49Base(SeleniumBase):
    def setUp(self):
        self.user = User(username='User A')
        self.passwd = 'hi'
        self.user.set_password(self.passwd)
        self.user.save()
        self.project = Project(name='A Project')
        self.project.save()
        self.project.project_members.add(self.user)
        self.project.save()
        self.iteration = Iteration(start_date='1990-01-01',
                                   end_date='2020-01-01',
                                   project=self.project)
        self.iteration.save()
        self.story = UserStory(name='ABC', project=self.project,
                               description='a userstory about abc',
                               iteration=self.iteration, planned=42, rank=1,
                               state=10, blocked=True)
        self.story.save()
        task_states = dict((v,k) for (k,v) in Task.STATES)
        self.task_a = Task(name="Task A", estimate=8, remaining=8,
                           state=task_states['In Progress'],
                           owner=self.user, user_story=self.story)
        self.task_a.save()
        self.task_b = Task(name="Task B", estimate=2, remaining=2,
                           state=task_states['Defined'],
                           owner=self.user, user_story=self.story)
        self.task_b.save()
                           
        super(TestUS49Base, self).setUp()
    def tearDown(self):
        self.project.delete()
        self.user.delete()
        super(TestUS49Base, self).tearDown()
        
class TestUS49(TestUS49Base):
    def load(self, task, summary, time_on_task=None, remaining=None, state=None):
        b = self.browser
        b.open("/log/")
        b.wait()
        b.click("xpath=//input[@type='radio'][@value='a%d']" % task.id)
        b.type("id_summary", summary)
        if time_on_task is not None:
            b.type("id_time_on_task", time_on_task)
        if remaining is not None:
            b.type("id_remaining", remaining)
        if state is not None:
            b.select("id_state", state)

        b.click("css=#content input[type=submit]")
        b.wait()
        

    def check_task(self, task, actuals, remaining, state):
        b = self.browser
        b.open(task.get_absolute_url())
        b.wait()
        self.assertEqual(float(b.get_text("css=.actuals")), actuals)
        self.assertEqual(float(b.get_text("css=.remaining")), remaining)
        self.assertEqual(b.get_text("css=.state"), state)


    def check_story(self, story, actuals, remaining, state):
        b = self.browser
        b.open(story.get_absolute_url())
        b.wait()
        self.assertEqual(float(b.get_text("css=#actuals")), actuals)
        self.assertEqual(float(b.get_text("css=#remaining")), remaining)
        self.assertEqual(b.get_text("css=#state"), state)


    def test_tc21(self):
        self.load(self.task_a, "testing", time_on_task="4", remaining="2")
        self.check_task(self.task_a, 4., 2., "In Progress")
        self.check_story(self.story, 4., 4., "In Progress")

    def test_tc22(self):
        self.load(self.task_a, "loading", time_on_task="4", remaining="2")
        self.load(self.task_a, "testing", time_on_task="4", state="Complete")
        self.check_task(self.task_a, 8., 0., "Complete")
        self.check_story(self.story, 8., 2., "In Progress")

    def test_tc28(self):
        self.load(self.task_a, "loading", time_on_task="4", remaining="2")
        self.load(self.task_a, "loading", time_on_task="4", state="Complete")
        self.load(self.task_b, "testing", time_on_task=10, state="Complete")
        self.check_story(self.story, 18, 0, "Completed")

    def test_tc27(self):
        self.load(self.task_a, "loading", time_on_task="4", remaining="2")
        self.load(self.task_a, "loading", time_on_task="4", state="Complete")
        self.load(self.task_b, "loading", time_on_task=10, state="Complete")
        self.load(self.task_a, "testing", time_on_task=1.33, remaining=.5, state="In Progress")
        self.check_task(self.task_a, 9.33, .5, "In Progress")
        self.check_story(self.story, 19.33, .5, "In Progress")

    def test_tc23(self):
        self.load(self.task_a, "loading", time_on_task="4", remaining="2")
        self.load(self.task_a, "testing", time_on_task=2)
        self.check_task(self.task_a, 6, 2, "In Progress")
        self.check_story(self.story, 6, 4, "In Progress")
