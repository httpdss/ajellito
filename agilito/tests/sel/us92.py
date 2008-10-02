from us49 import TestUS49Base
from agilito.models import TestCase, UserStory, Task, TestResult
from base import BASE_URL

class TestUS92(TestUS49Base):

    def test_adding_us_returns_to_iteration_view(self):
        """
        I am on iteration view and hit the pencil button to "edit". 
        I make changes and save. This should take me back to the iteration view
        (not the backlog!)
        """
        b = self.browser
        b.click("link=Iteration")
        b.wait()
        last_location = b.get_location()
        b.click("link=Add User Story")
        
        b.wait()        
        b.type("id_name", "A sample detailed user story")
        b.type("id_description", "This is a detailed user story")
        b.type("id_planned", "10")
        b.type("id_rank", "50")
        b.type("id_state", "10")
        b.click("id_blocked")
        b.click("xpath=id('content')/form/input")
        b.wait()
        
        location = b.get_location()
        self.assertEqual(location, last_location)


    def test_editing_us_returns_to_iteration_view(self):
    
        """
        I am on US details page and hit "edit" button. When I save, this should
        take me back to the US details back (not the backlog!)
        """

        b = self.browser
        b.click("link=Iteration")
        b.wait()
        last_location = b.get_location()
        b.click("xpath=id('edit_us_%d')/a/img" % self.story.id)
        b.wait()        
        b.type("id_name", "A sample detailed user story")
        b.type("id_description", "This is a detailed user story")
        b.type("id_planned", "10")
        b.type("id_rank", "50")
        b.type("id_state", "10")
        b.click("id_blocked")
        b.click("xpath=id('content')/form/input")
        b.wait()
        
        location = b.get_location()
        self.assertEqual(location, last_location)
        
    def test_editing_a_us_from_us_view_returns_to_us_view(self):

        b = self.browser
        b.click("link=Iteration")
        b.wait()

        b.click("link=ABC")
        b.wait()
        last_location = b.get_location()
        b.click("link=Edit User Story")
        b.wait()        
        b.type("id_name", "A sample detailed user story")
        b.type("id_description", "This is a detailed user story")
        b.type("id_planned", "10")
        b.type("id_rank", "50")
        b.type("id_state", "10")
        b.click("id_blocked")
        b.click("xpath=id('content')/form/input")
        b.wait()
        
        location = b.get_location()
        self.assertEqual(location, last_location)


    def test_adding_a_us_from_backlog_returns_to_backlog(self):

        b = self.browser
        b.click("link=Backlog")
        b.wait()
        last_location = b.get_location()

        b.click("link=Add User Story")
        b.wait()
        b.type("id_name", "A sample detailed user story")
        b.type("id_description", "This is a detailed user story")
        b.type("id_planned", "10")
        b.type("id_rank", "50")
        b.type("id_state", "10")
        b.click("id_blocked")
        b.click("xpath=id('content')/form/input")
        b.wait()
        
        location = b.get_location()
        self.assertEqual(location, last_location)

    def test_deleting_a_us_from_backlog_returns_to_backlog(self):

        b = self.browser
        b.click("link=Backlog")
        b.wait()
        last_location = b.get_location()

        b.click("link=Add User Story")
        b.wait()
        b.type("id_name", "A sample detailed user story to be deleted")
        b.type("id_description", "This is a detailed user story")
        b.type("id_planned", "10")
        b.type("id_rank", "50")
        b.type("id_state", "10")
        b.click("id_blocked")
        b.click("xpath=id('content')/form/input")
        b.wait()
        
        self.assertEqual(last_location, b.get_location())
        last_location = b.get_location()

        story = UserStory.objects.filter(iteration=None)[0]        

        b.click("xpath=id('delete_us_%d')/a/img" % story.id)
        b.wait()
        b.click("xpath=id('content')/form/div/input[2]")      
        b.wait()

        self.assertEqual(last_location, b.get_location())

    def test_deleting_a_us_from_iteration_returns_to_iteration(self):

        b = self.browser
        b.click("link=Iteration")
        b.wait()
        last_location = b.get_location()

        b.click("xpath=id('delete_us_%d')/a/img" % self.story.id)
        b.wait()
        b.click("xpath=id('content')/form/div/input[2]")      
        b.wait()
        self.assertEqual(last_location, b.get_location())

    def test_deleting_a_us_from_us_view_is_not_in_iteration_returns_to_backlog(self):

        b = self.browser
        b.click("link=Backlog")
        b.wait()
        last_location = b.get_location()
        backlog_url = b.get_location()

        b.click("link=Add User Story")
        b.wait()
        b.type("id_name", "A sample detailed user story to be deleted")
        b.type("id_description", "This is a detailed user story")
        b.type("id_planned", "10")
        b.type("id_rank", "50")
        b.type("id_state", "10")
        b.click("id_blocked")
        b.click("xpath=id('content')/form/input")
        b.wait()
        
        self.assertEqual(last_location, b.get_location())
        
        b.click("link=A sample detailed user story to be deleted")
        b.wait()
        
        last_location = b.get_location()

        b.click("link=Delete")
        b.wait()
        b.click("xpath=id('content')/form/div/input[2]")      
        b.wait()

        self.assertNotEqual(last_location, b.get_location())
        self.assertEqual(backlog_url, b.get_location())

    def test_adding_a_us_from_url(self):

        b = self.browser
        b.open(BASE_URL+"1/backlog/userstory/add")
        b.wait()

        b.type("id_name", "A sample detailed user story to be deleted")
        b.type("id_description", "This is a detailed user story")
        b.type("id_planned", "10")
        b.type("id_rank", "50")
        b.type("id_state", "10")
        b.click("id_blocked")
        b.click("xpath=id('content')/form/input")
        b.wait()

        self.assertEqual(BASE_URL+"1/backlog/", b.get_location())
        
    def test_edit_a_us_from_url(self):

        b = self.browser
        b.open(BASE_URL+"1/userstory/1/edit/")
        b.wait()

        b.type("id_name", "A sample detailed user story to be deleted")
        b.type("id_description", "This is a detailed user story")
        b.type("id_planned", "10")
        b.type("id_rank", "50")
        b.type("id_state", "10")
        b.click("id_blocked")
        b.click("xpath=id('content')/form/input")
        b.wait()

        self.assertEqual(BASE_URL+"1/iteration/1/", b.get_location())

    def test_add_a_task_to_a_us_from_url(self):

        b = self.browser
        b.open(BASE_URL+"1/userstory/1/task/add")
        b.wait()

        b.type("id_name", "A sample task")
        b.click("xpath=id('content')/form/input")
        b.wait()

        self.assertEqual(BASE_URL+"1/userstory/1/", b.get_location())

    def test_add_a_testcase_to_a_us_from_url(self):

        b = self.browser
        b.open(BASE_URL+"1/userstory/1/testcase/add")
        b.wait()

        b.type("id_name", "A sample testcase")
        b.click("xpath=id('content')/form/input")
        b.wait()

        self.assertEqual(BASE_URL+"1/userstory/1/", b.get_location())

    def test_add_a_testcase_and_delete_from_a_us_from_url(self):

        b = self.browser
        b.open(BASE_URL+"1/userstory/1/testcase/add")
        b.wait()

        b.type("id_name", "A sample testcase")
        b.click("xpath=id('content')/form/input")
        b.wait()

        self.assertEqual(BASE_URL+"1/userstory/1/", b.get_location())

        test_case = TestCase.objects.filter(user_story__id=1)[0]
        b.open((BASE_URL+"1/userstory/1/testcase/%d/delete/") % test_case.id)
        b.wait()
    
        b.click("xpath=id('content')/form/div/input[2]")      
        b.wait()

        self.assertEqual(BASE_URL+"1/userstory/1/", b.get_location())

    def test_add_a_task_and_delete_from_a_us_from_url(self):

        b = self.browser
        b.open(BASE_URL+"1/userstory/1/task/add")
        b.wait()

        b.type("id_name", "A sample task")
        b.click("xpath=id('content')/form/input")
        b.wait()

        self.assertEqual(BASE_URL+"1/userstory/1/", b.get_location())

        task = Task.objects.filter(user_story__id=1)[0]
        b.open((BASE_URL+"1/userstory/1/task/%d/delete/") % task.id)
        b.wait()
    
        b.click("xpath=id('content')/form/div/input[2]")      
        b.wait()

        self.assertEqual(BASE_URL+"1/userstory/1/", b.get_location())

    def test_add_a_testcase_add_testresult_from_url(self):

        b = self.browser
        b.open(BASE_URL+"1/userstory/1/testcase/add")
        b.wait()

        b.type("id_name", "A sample testcase")
        b.click("xpath=id('content')/form/input")
        b.wait()

        self.assertEqual(BASE_URL+"1/userstory/1/", b.get_location())

        test_case = TestCase.objects.filter(user_story__id=1)[0]
        b.open((BASE_URL+"1/userstory/1/testcase/%d/testresult/add") % test_case.id)
        b.wait()

        b.type("id_comments", "blah")
        b.click("xpath=id('content')/form/input")
        b.wait()

        self.assertEqual((BASE_URL+"1/userstory/1/testcase/%d/") % test_case.id, b.get_location())

    def test_add_a_testcase_add_testresult_and_delete_testresult_from_url(self):

        b = self.browser
        b.open(BASE_URL+"1/userstory/1/testcase/add")
        b.wait()

        b.type("id_name", "A sample testcase")
        b.click("xpath=id('content')/form/input")
        b.wait()

        self.assertEqual(BASE_URL+"1/userstory/1/", b.get_location())

        test_case = TestCase.objects.filter(user_story__id=1)[0]
        b.open((BASE_URL+"1/userstory/1/testcase/%d/testresult/add") % test_case.id)
        b.wait()

        b.type("id_comments", "blah")
        b.click("xpath=id('content')/form/input")
        b.wait()

        self.assertEqual((BASE_URL+"1/userstory/1/testcase/%d/") % test_case.id, b.get_location())
    
        testresult = TestResult.objects.filter(test_case=test_case)[0]
        b.open((BASE_URL+"1/userstory/1/testcase/%d/testresult/%d/delete/") % (test_case.id, testresult.id))
        b.wait()

        b.click("xpath=id('content')/form/div/input[2]")      
        b.wait()

        self.assertEqual((BASE_URL+"1/userstory/1/testcase/%d/") % test_case.id, b.get_location())

