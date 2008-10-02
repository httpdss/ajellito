from us49 import TestUS49Base
from agilito.models import Task

class TestUS26(TestUS49Base):
    # a very simple test, as no test cases were provided
    def test_simple(self):
        pre = Task.objects.count()
        b = self.browser
        b.click("link=Iteration")
        b.wait()
        b.click("link=ABC")
        b.wait()
        b.click("link=add a task")
        b.wait()
        b.type("id_name", "hi")
        b.click("css=#content input[type=submit]")
        b.wait()
        
        self.assertEqual(Task.objects.count(), pre+1)
