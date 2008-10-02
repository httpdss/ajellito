from base import SeleniumBase, random_name
from agilito.models import Project, User

class TestUS34(SeleniumBase):
    do_login = do_logout = False
    def setUp(self):
        self.ABC = Project(name='ABC')
        self.ABC.save()
        self.DEF = Project(name='DEF')
        self.DEF.save()
        self.EFG = Project(name='EFG')
        self.EFG.save()
        self.A = User(username='A')
        self.A.set_password('abc')
        self.A.save()
        self.B = User(username='B')
        self.B.set_password('def')
        self.B.save()
        self.C = User(username='C')
        self.C.set_password('ghi')
        self.C.save()
        self.ABC.project_members.add(self.A)
        self.ABC.project_members.add(self.B)
        self.DEF.project_members.add(self.B)
        super(TestUS34, self).setUp()

    def tearDown(self):
        for obj in (self.ABC, self.DEF, self.EFG, self.A, self.B, self.C):
            obj.delete()
        super(TestUS34, self).tearDown()

    def test_tc16(self):
        self.login(username='a', password='abc')
        self.assertEqual(self.browser.get_text('error-message'),
                         u'Username / password combination does not exist')

    def test_tc17(self):
        self.login(username='A', password='Abc')
        self.assertEqual(self.browser.get_text('error-message'),
                         u'Username / password combination does not exist')

    def test_tc18(self):
        self.login(username='A', password='abc')
        opts = self.browser.get_select_options('css=#project-selection select')
        self.assertEqual(opts, [u'ABC'])
    def test_tc19(self):
        self.login(username='B', password='def')
        opts = self.browser.get_select_options('css=#project-selection select')
        self.assertEqual(opts, [u'ABC', u'DEF'])
