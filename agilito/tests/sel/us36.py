from us49 import TestUS49Base
from agilito.models import UserStory

class TestUS36(TestUS49Base):
    def setUp(self):
        super(TestUS36, self).setUp()
        b = self.browser
        b.click("link=Iteration")
        b.wait()
        b.click("link=ABC")
        b.wait()

    def test_tc38_all_US_fields_available_from_admin(self):
#         print '*'*100
#         print b.get_html_source()
#         print '*'*100
        for field in UserStory._meta.fields:
            if field.name != 'id' and field.name != 'name':
                self.assert_(self.browser.get_text("id="+field.name))

    def test_tc38_tr15_some_fields_are_repeated(self):
        for field in UserStory._meta.fields:
            if field.name != 'id' and field.name != 'name': # the name is in the title
                self.assertEqual(self.browser.get_xpath_count("//*[@id='%s']" % field.name), u'1')
