from us49 import TestUS49Base, SeleniumBase
from base import BASE_URL
from agilito.models import User


class TestUS320(TestUS49Base):
    
    def test_simple_password_change(self):
        """
        Just checks if I really if I can change the user password
        """
        b = self.browser
        b.click("link=Change password")
        b.wait()
        b.type("id_old_password", "hi")
        b.type("id_new_password1", "bye")
        b.type("id_new_password2", "bye")
        b.click("xpath=id('content')/form/p[4]/input")
        b.wait()
        for i in xrange(20):
            b.wait()

        self.assertEqual(BASE_URL+'accounts/changepassword/done/', b.get_location())
        self.assert_(User.objects.get(username='User A').check_password('bye'))

    
