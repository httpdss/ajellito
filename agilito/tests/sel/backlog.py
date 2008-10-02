from base import SeleniumBase
from agilito.models import Project, User, UserStory

class TestBacklogQuickAdd(SeleniumBase):
    def setUp(self):
        self.user = User(username='User AB')
        self.passwd = 'hi'
        self.user.set_password(self.passwd)
        self.user.save()
        self.project = Project(name='A Project')
        self.project.save()
        self.project.project_members.add(self.user)
        self.project.save()

        self.story1 = UserStory(name='User Story A', rank=3, planned=3, project=self.project)
        self.story1.save()
        self.story2 = UserStory(name='User Story B', rank=2, planned=8, project=self.project)
        self.story2.save()
        self.story3 = UserStory(name='User Story C', rank=1, planned=5, project=self.project)
        self.story3.save()
                           
        super(TestBacklogQuickAdd, self).setUp()

    def tearDown(self):
        self.project.delete()
        self.user.delete()
        for x in self.story1, self.story2, self.story3:
            x.delete()
        super(TestBacklogQuickAdd, self).tearDown()
        
    def test_tc4(self):
        self.login(username='User AB', password='hi')
        #sel.open("/accounts/login/")
        #sel.type("id_username", "User B")
        #sel.type("id_password", "hi")
        #sel.click("//input[@value='login']")
        b = self.browser
        b.click("link=Backlog")
        b.wait()
        b.click("create-user-story")
        b.type("id_name", "A sample user story")
        b.click("us-create")
        self.assertEqual(b.get_text("us-span-4"),
                         "A sample user story")
        

class TestBacklogAddUSDetailed(SeleniumBase):
    def setUp(self):
        self.user = User(username='User BBB')
        self.passwd = 'hi'
        self.user.set_password(self.passwd)
        self.user.save()
        self.project = Project(name='A Project BB')
        self.project.save()
        self.project.project_members.add(self.user)
        self.project.save()

        self.story1 = UserStory(name='User Story A', rank=3, planned=3, project=self.project)
        self.story1.save()
        self.story2 = UserStory(name='User Story B', rank=2, planned=8, project=self.project)
        self.story2.save()
        self.story3 = UserStory(name='User Story C', rank=1, planned=5, project=self.project)
        self.story3.save()
                           
        super(TestBacklogAddUSDetailed, self).setUp()

    def tearDown(self):
        self.project.delete()
        self.user.delete()
        for x in self.story1, self.story2, self.story3:
            x.delete()
        super(TestBacklogAddUSDetailed, self).tearDown()
        
    def test_create_complete_us(self):
        self.login(username='User BBB', password='hi')
        b = self.browser
        b.click("link=Backlog")
        b.wait()
        b.click("create-detailed-user-story")
        b.type("id_name", "A sample detailed user story")
        b.type("id_description", "This is a detailed user story")
        b.type("id_planned", "10")
        b.type("id_rank", "50")
        b.type("id_state", "10")
        b.click("id_blocked")
        b.click("us-create")
        self.assertEqual(b.get_text("us-span-4"),
                         "A sample detailed user story")
