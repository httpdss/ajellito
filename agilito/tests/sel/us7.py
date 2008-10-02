from us49 import TestUS49Base
from agilito.models import UserStory

class TestUS7(TestUS49Base):
    def test_can_delete_userstory(self):

        b = self.browser
        b.click("link=Iteration")
        b.wait()
        b.click("link=ABC")
        b.wait()
        b.click("link=Delete")
        b.wait()
        b.click("css=#content input[type=submit]")
        for i in xrange(20):
            b.wait()
        
        self.assertEqual(UserStory.objects.count(), 0)

