from us49 import TestUS49Base
from agilito.models import TestCase, UserStory

class TestUS71(TestUS49Base):

    def test_add_testcase_simple(self):

        pre = TestCase.objects.count()
        b = self.browser
        b.click("link=Iteration")
        b.wait()
        b.click("link=ABC")
        b.wait()
        b.click("link=add a test case")
        b.wait()
        b.type("id_name", "hi")
        b.click("css=#content input[type=submit]")
        for i in xrange(15):        
            b.wait()
        self.assertEqual(TestCase.objects.count(), pre+1)

    def test_delete_testcase_simple(self):
        
        test_case = TestCase(name='ABC Test', description='Test', priority=10,
                             user_story=self.story)
        test_case.save()
        
        pre = TestCase.objects.count()
        b = self.browser
        b.click("link=Iteration")
        b.wait()
        b.click("link=ABC")
        b.wait()
        b.click("xpath=id('delete_testcase_%d')/a/img" % (test_case.id))
        b.wait()
        b.wait()
        b.click("xpath=id('content')/form/div/input[2]")      
        # wait a bit longer that usual, else error.     
        for i in xrange(15):        
            b.wait()
        self.assertEqual(TestCase.objects.count(), pre-1)
 
    def test_edit_testcase_simple(self):
        
        test_case = TestCase(name='ABC Test', description='Test', priority=10,
                             user_story=self.story)
        test_case.save()

        pk = test_case.id        

        pre = TestCase.objects.count()
        b = self.browser
        b.click("link=Iteration")
        b.wait()
        b.click("link=ABC")
        b.wait()
        b.click("xpath=id('edit_testcase_%d')/a/img" % (test_case.id))
        b.wait()
        b.type("id_name", "hi")
        b.type("id_description", "bye")        
        b.click("css=#content input[type=submit]")
        for i in xrange(15):        
            b.wait()
        self.assertEqual(TestCase.objects.count(), pre)

        # reload test_case
        test_case = TestCase.objects.get(pk=pk)
        self.assertEqual(test_case.name, 'hi')
        self.assertEqual(test_case.description, 'bye')
        self.assertEqual(test_case.user_story.id, self.story.id)

    def test_edit_change_us(self):

        other_story = UserStory(name='DEF', project=self.project,
                                description='a userstory about def',
                                iteration=self.iteration, planned=42, rank=2,
                                state=20, blocked=False)
        other_story.save()

        test_case = TestCase(name='ABC Test', description='Test', priority=10,
                             user_story=self.story)
        test_case.save()

        pk = test_case.id        

        pre = TestCase.objects.count()
        b = self.browser
        b.click("link=Iteration")
        b.wait()
        b.click("link=ABC")
        b.wait()
        b.click("xpath=id('edit_testcase_%d')/a/img" % (test_case.id))
        b.wait()
        b.type("id_name", "hi")
        b.type("id_description", "bye")
        b.select("id_user_story", "US2: DEF")
        self.assertEqual(b.get_selected_label("id_user_story"), "US2: DEF") 
        b.click("css=#content input[type=submit]")
        for i in xrange(15):        
            b.wait()
        self.assertEqual(TestCase.objects.count(), pre)

        # reload test_case
        test_case = TestCase.objects.get(pk=pk)
        self.assertEqual(test_case.name, 'hi')
        self.assertEqual(test_case.description, 'bye')
        self.assertEqual(test_case.user_story.id, other_story.id)

        test_case.delete()
        other_story.delete()

    def test_edit_testcase_simple_from_testcase_view(self):
        
        test_case = TestCase(name='ABC Test', description='Test', priority=10,
                             user_story=self.story)
        test_case.save()

        pk = test_case.id        

        pre = TestCase.objects.count()
        b = self.browser
        b.click("link=Iteration")
        b.wait()
        b.click("link=ABC")
        b.wait()
        b.click("link=ABC Test")
        b.wait()
        b.click("xpath=id('edit_testcase_%d')/a" % (test_case.id))
        b.wait()
        b.type("id_name", "hi")
        b.type("id_description", "bye")        
        b.click("css=#content input[type=submit]")
        for i in xrange(15):        
            b.wait()
        self.assertEqual(TestCase.objects.count(), pre)

        # reload test_case
        test_case = TestCase.objects.get(pk=pk)
        self.assertEqual(test_case.name, 'hi')
        self.assertEqual(test_case.description, 'bye')
        self.assertEqual(test_case.user_story.id, self.story.id)
        test_case.delete()

    def test_delete_testcase_simple_from_testcase_view(self):
        
        test_case = TestCase(name='ABC Test', description='Test', priority=10,
                             user_story=self.story)
        test_case.save()
        
        pre = TestCase.objects.count()
        b = self.browser
        b.click("link=Iteration")
        b.wait()
        b.click("link=ABC")
        b.wait()
        b.click("link=ABC Test")
        b.wait()
        b.click("xpath=id('delete_testcase_%d')/a" % (test_case.id))
        b.wait()
        b.click("xpath=id('content')/form/div/input[2]")      
        for i in xrange(15):        
            b.wait()

        self.assertEqual(TestCase.objects.count(), pre-1)



