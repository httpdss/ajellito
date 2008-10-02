from us49 import TestUS49Base
from agilito.models import TestCase, UserStory, TestResult, User
from base import BASE_URL
import re

class TestUS104(TestUS49Base):

    def test_add_testcase_andthen_testresult_simple(self):

        pre = TestCase.objects.count(), TestResult.objects.count()

        b = self.browser
        b.click("link=Iteration")
        b.wait()
        b.click("link=ABC")
        b.wait()
        last_location = b.get_location()
        b.click("link=add a test case")
        b.wait()
        b.type("id_name", "hi")
        b.click("css=#content input[type=submit]")
        b.wait()

        self.assertEqual(last_location, b.get_location())


        b.click("link=hi")
        b.wait()

        last_location = b.get_location()


        b.click("link=add a test result")
        b.wait()
        b.type("id_comments", "this is a test")
        b.select("id_result", "Pass")
        b.select("id_tester", "User A")
        b.type("id_date", "2008-08-01")
        opt = b.get_select_options("id_test_case")[1]
        b.select("id_test_case", opt)
        b.click("css=#content input[type=submit]")

        # wait a tad bit more...        
        for x in xrange(15):
            b.wait()
        self.assertEqual(last_location, b.get_location())

        self.assertEqual(TestCase.objects.count(), pre[0]+1)
        self.assertEqual(TestResult.objects.count(), pre[1]+1)

    def test_add_testcase_andthen_testresult_simple_on_us_view(self):

        test_case = TestCase(name='ABC Test', description='Test', priority=10,
                             user_story=self.story)
        test_case.save()

        pre = TestResult.objects.count()

        b = self.browser
        b.click("link=Iteration")
        b.wait()
        b.click("link=ABC")
        b.wait()
        last_location = b.get_location()

        b.click("xpath=id('add_testresult_%d')/a/img" % test_case.id)
        b.wait()
        b.type("id_comments", "this is a test")
        b.select("id_result", "Pass")
        b.select("id_tester", "User A")
        b.type("id_date", "2008-08-01")
        opt = b.get_select_options("id_test_case")[1]
        b.select("id_test_case", opt)
        b.click("css=#content input[type=submit]")
        b.wait()
        for x in xrange(15):
            b.wait()
        self.assertEqual(TestResult.objects.count(), pre+1)
        self.assertEqual(last_location, b.get_location())
   
        test_case.delete()

    def test_delete_testresult_simple(self):
        from datetime import datetime        

        test_case = TestCase(name='ABC Test', description='Test', priority=10,
                             user_story=self.story)
        test_case.save()
        
        test_result = TestResult(result=1, comments='Test', tester=User.objects.all()[0],
                                 test_case=test_case, date=datetime.today())
        test_result.save()

        pre = TestResult.objects.count()
        b = self.browser
        b.click("link=Iteration")
        b.wait()
        b.click("link=ABC")
        b.wait()
        b.click("link=ABC Test")
        b.wait()
        b.click("xpath=id('delete_testresult_%d')/a/img" % (test_result.id))
        b.wait()
        b.click("xpath=id('content')/form/div/input[2]")      
        for x in xrange(20):
            b.wait()

        self.assertEqual(TestResult.objects.count(), pre-1)


    def test_edit_testresutl_simple(self):
        from datetime import datetime

        test_case = TestCase(name='ABC Test', description='Test', priority=10,
                             user_story=self.story)
        test_case.save()
        
        test_result = TestResult(result=1, comments='Test', tester=User.objects.all()[0],
                                 test_case=test_case, date=datetime.today())
        test_result.save()

        b = self.browser
        b.click("link=Iteration")
        b.wait()
        b.click("link=ABC")
        b.wait()
        b.click("link=ABC Test")
        b.wait()
        last_location = b.get_location()

        b.click("xpath=id('edit_testresult_%d')/a/img" % (test_result.id))
        b.wait()
        b.type("id_comments", "this is a test 2")
        b.select("id_result", "Fail")
        b.select("id_tester", "User A")
        b.type("id_date", "2008-08-02")
        opt = b.get_select_options("id_test_case")[1]
        b.select("id_test_case", opt)
        b.click("css=#content input[type=submit]")
        for x in xrange(15):
            b.wait()

        test_result = TestResult.objects.get(pk=test_result.id)
        self.assertEqual(test_result.result, 0)
        self.assertEqual(test_result.comments, "this is a test 2")
        self.assertEqual(test_result.date, datetime(2008, 8, 2, 0, 0))

        # But anyway lets just check the url
        self.assertEqual(last_location, b.get_location())

        test_result.delete()
        test_case.delete()

    def test_delete_testresult_from_result_view(self):
        from datetime import datetime        

        test_case = TestCase(name='ABC Test', description='Test', priority=10,
                             user_story=self.story)
        test_case.save()
        
        test_result = TestResult(result=1, comments='Test', tester=User.objects.all()[0],
                                 test_case=test_case, date=datetime.today())
        test_result.save()

        pre = TestResult.objects.count()
        b = self.browser
        b.click("link=Iteration")
        b.wait()
        b.click("link=ABC")
        b.wait()
        b.click("link=Pass")
        b.wait()
        b.click("xpath=id('delete_testresult_%d')/a/img" % (test_result.id))
        b.wait()
        b.click("xpath=id('content')/form/div/input[2]")      
        b.wait()
        self.assertEqual(TestResult.objects.count(), pre-1)
        test_case.delete()

    def test_delete_testcase_with_testresult(self):
        from datetime import datetime        

        test_case = TestCase(name='ABC Test', description='Test', priority=10,
                             user_story=self.story)
        test_case.save()
        
        test_result = TestResult(result=1, comments='Test', tester=User.objects.all()[0],
                                 test_case=test_case, date=datetime.today())
        test_result.save()

        test_result = TestResult(result=2, comments='Test', tester=User.objects.all()[0],
                                 test_case=test_case, date=datetime.today())
        test_result.save()

        pre = (TestCase.objects.count(), TestResult.objects.count(),)
        b = self.browser
        b.click("link=Iteration")
        b.wait()
        b.click("link=ABC")
        b.wait()
        last_location = b.get_location()
        b.click("xpath=id('delete_testcase_%d')/a" % (test_case.id))
        b.wait()
        b.click("xpath=id('content')/form/div/input[2]")      
        for i in xrange(15):        
            b.wait()
        self.assertEqual(last_location, b.get_location())
        self.assertEqual(TestResult.objects.count(), pre[1]-2)
        self.assertEqual(TestCase.objects.count(), pre[0]-1)

