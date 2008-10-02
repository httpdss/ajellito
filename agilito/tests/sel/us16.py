from us49 import TestUS49Base
from agilito.models import Task

class TestUS16(TestUS49Base):
    
    def test_simple(self):
        """
        Just checks if I really deleted the task
        """

        pre = Task.objects.count()
        b = self.browser
        b.click("link=Iteration")
        b.wait()
        b.click("link=ABC")
        b.wait()
        b.click("css=img[title=delete]:first-child")
        b.wait()
        b.click("xpath=id('content')/form/div/input[2]")      
        for i in xrange(20):
            b.wait()
        self.assertEqual(Task.objects.count(), pre-1)
