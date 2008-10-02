from base import SeleniumBase, random_name
from agilito.models import Project, User, UserStory

class TestUS21(SeleniumBase):
    def setUp(self):
        self.passwd = 'hola' # random_name()
        self.user = User(username=random_name())
        self.user.set_password(self.passwd)
        self.user.save()
        self.proj1 = Project(name=random_name())
        self.proj2 = Project(name=random_name())
        for proj in self.proj1, self.proj2:
            proj.save()
            proj.project_members.add(self.user)
            proj.save()
        self.us1 = UserStory(name=random_name(), project=self.proj1)
        self.us1.save()
        self.us2 = UserStory(name=random_name(), project=self.proj2)
        self.us2.save()
        super(TestUS21, self).setUp()

    def tearDown(self):
        for obj in self.user, self.proj1, self.proj2, self.us1, self.us2:
            obj.delete()
        super(TestUS21, self).tearDown()

    def test_user_assigned_to_multiple_projects_switch_to_other_project(self):
        us_locator = "css=#user-story-list td.name a"
        b = self.browser
        b.click("link=Backlog")
        b.wait()
        this_us = b.get_text(us_locator)
        if this_us == self.us1.name:
            target_project, target_story = self.proj2, self.us2
        else:
            assert this_us == self.us2.name
            target_project, target_story = self.proj1, self.us1
        b.select("//li[@id='project-selection']/select",
                 "label=" + target_project.name)
        b.wait()
        self.assertEqual(b.get_text(us_locator), target_story.name)
        
