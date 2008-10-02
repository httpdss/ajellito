from django import test
from django.test.client import Client
import datetime

from agilito.models import User, UserStory, Task, TestCase, Project, Iteration,\
    TestResult, TaskLog, Release, UserStoryAttachment

def _if_is_none_else(item,  rv_case_none,  fun_case_not_none):
    if item is None:
        return rv_case_none
    else:
        return fun_case_not_none(item)


class TTW(object):
    username = 'chipaca'
    password = 'ScDQ4ESIG9O9dU1vCaD8'
    def login(self):
        self.assert_(self.client.login(username=self.username,
                                       password=self.password))
        return User.objects.get(username=self.username)

    def setUp(self):
        super(TTW, self).setUp()
        self.client = Client()

class TestTasks(test.TestCase, TTW):
    fixtures = ['database_dump.json']
    _class = Task
    _count = 412 # 47, oldest value 29 

    def test_query_empty(self):
        """
        Check if you can search on tasks
        """
        result = self._class.query('')
        self.assertEqual(len(result), self._count)

    def test_query_empty_with_project(self):
        """
        Check if you can search on tasks using a project id
        """
        result = self._class.query('', project_id=1)
        self.assertEqual(len(result), 121) # 47

    def test_has_absolute_url(self):
        obj = self._class.objects.all()[0]
        self.assertNotEqual(getattr(obj, 'get_absolute_url', None), None)

    def test_absolute_url_exists(self):
        obj = self._class.objects.all()[0]
        self.login()
        page = obj.get_absolute_url()
        response = self.client.get(page)
        self.assertNotEqual(response.status_code, 404)

class TestUserStories(TestTasks):
    _class = UserStory
    _count = 445 # older 55, oldest value 36

    def test_query_empty_with_project(self):
        """
        Check if you can search on tasks using a project id
        """
        result = self._class.query('', project_id=1)
        self.assertEqual(len(result), 87) #old value 53

class TestTestCases(TestTasks):
    _class = TestCase
    _count = 108 # 32 older , oldest value 20

    def test_query_empty_with_project(self):
        """
        Check if you can search on tasks using a project id
        """
        result = self._class.query('', project_id=1)
        self.assertEqual(len(result), 80) #old value 32

class TestSearchTTW(test.TestCase, TTW):
    fixtures = ['database_dump.json']

    def test_needs_login(self):
        response = self.client.get('/1/search/')
        self.assertEqual(response.status_code, 302)
        self.assert_('/login/' in response['Location'])

    def test_shows_form(self):
        self.login()
        response = self.client.get('/1/search/')
        self.assertEqual(response.status_code, 200)

    def test_does_search(self):
        self.login()
        response = self.client.get('/1/search/',
                                   {'query': 'owner'})

        self.assertEqual(response.status_code, 200)
        # just checking to see if it actually found something :)
        self.assert_(response.content.count('owner') > 1)

    def test_does_search_returns_ordered_by_id(self):
        self.login()
        response = self.client.get('/1/search/',
                                   {'query': 'owner'})

        self.assertEqual(response.status_code, 200)
        # just checking to see if it actually found something :)
        self.assert_(response.content.count('owner') > 1)
 
        # check if they are in order.
        ids = [ o.id for o in response.context[0]['object_list']]
        result = True
        tmp = ids[0]
        for x in ids:
            if tmp > x:
               result = False
            tmp = x

        self.assert_(result)

class TestProjectReachability(test.TestCase, TTW):
    fixtures = ['database_dump.json']
    def setUp(self):
        super(TestProjectReachability, self).setUp()

    def test_cannot_reach_unassigned_project(self):
        user = self.login()
        p = Project(name='test')
        p.save()
        response = self.client.get('/%d/backlog/' % p.id)
        self.assertEqual(response.status_code, 404)

    def test_can_reach_assigned_project(self):
        user = self.login()
        p = user.project_set.all()[0]
        response = self.client.get('/%d/backlog/' % p.id)
        self.assertEqual(response.status_code, 200)

class TestURLs(TTW):

    fixtures =  ['database_dump.json']

    def setUp(self):
        super(TestURLs, self).setUp()
        pqset = Project.objects.all()
        for p in pqset:
            p.project_members.add(User.objects.get(username=self.username))

    def test_has_absolute_url(self):
        obj = self._class.objects.all()[0]
        self.assertNotEqual(getattr(obj, 'get_absolute_url', None), None)

    def test_absolute_url_exists(self):
        obj = self._class.objects.all()[0]
        self.login()
        page = obj.get_absolute_url()
        response = self.client.get(page)
        self.assertNotEqual(response.status_code, 404)

class TestIterationURLs(TestURLs, test.TestCase):

    def setUp(self):
        super(TestIterationURLs, self).setUp()        
        self._class = Iteration
        self.project = Project.objects.get(id=5)
        self.project.project_members.add(User.objects.get(username='chipaca'))


    def test_get_absolute_url_correct(self):
        obj = self._class.objects.all()[0]        
        url = '/%s/iteration/%d/' % (obj.project.id, obj.id)
        self.assertEqual(url, obj.get_absolute_url())

    def test_get_absoulte_url_displays_correct_iteration(self):
        obj = self._class.objects.all()[0]
        self.login()
        page = obj.get_absolute_url()
        response = self.client.get(page)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(obj.id, response.context[0]['current_iteration'].id)

    def test_url_with_iteration_id_not_related_to_project_returns_404(self):
        itr = Iteration.objects.filter(project=1)[0]
        self.login()
        response = self.client.get(itr.get_absolute_url())        
        self.assertEqual(response.status_code, 200)
        response = self.client.get(self.project.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        url = '/%s/iteration/%d/' % (self.project.id, itr.id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_iter_hours_url_with_iter_id_not_related_to_project_returns_404(self):
        itr = Iteration.objects.filter(project=1)[0]
        self.login()
        response = self.client.get(itr.get_absolute_url())        
        self.assertEqual(response.status_code, 200)
        response = self.client.get(self.project.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        url = '/%s/iteration/%d/hours/' % (self.project.id, itr.id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_current_iteration_status(self):
        from agilito.views import _get_iteration
        from datetime import datetime       
        obj = _get_iteration(1, datetime.today())
        url = '/%s/iteration/' % obj.project.id
        self.login()
        response = self.client.get(url)           
        self.assertEqual(response.status_code, 200)
        self.assertEqual(obj.id, response.context[0]['current_iteration'].id)

class TestIterationViews(test.TestCase):
    fixtures = ['database_dump.json']

    def setUp(self):
        self.project_id = 1

    def test__get_iteration_current_date_eq_end_of_iteration(self):
        from agilito.views import _get_iteration
        from datetime import date        
        
        iteration = _get_iteration(self.project_id, date(2008,07,25))
        self.assertEqual(iteration.id, 2)
        self.assertEqual(iteration.name, 'Iteration 1')
        
    def test__get_iteration_current_date_eq_in_between_iteration(self):
        from agilito.views import _get_iteration
        from datetime import date        
       
        iteration = _get_iteration(self.project_id, date(2008,07,21))
        self.assertEqual(iteration.id, 2)
        self.assertEqual(iteration.name, 'Iteration 1')

    def test__get_iteration_current_date_eq_start_of_second_iter(self):
        from agilito.views import _get_iteration
        from datetime import date        
        
        iteration = _get_iteration(self.project_id, date(2008,07,28))
        self.assertEqual(iteration.id, 3)
        self.assertEqual(iteration.name, 'Iteration 2')


    def test__get_iteration_current_date_beyond_all_iterations_end_date(self):
        from agilito.views import _get_iteration
        from datetime import date        
        
        iteration = _get_iteration(self.project_id, date(2030,01,01))
        latest = Iteration.objects.filter(project__id=self.project_id).latest('start_date')
        self.assertEqual(iteration.id, latest.id)
        self.assertEqual(iteration.name, latest.name)
        
    def test__get_iteration_date_beyond_an_iteration_but_not_before_start_of_next(self):
        from agilito.views import _get_iteration
        from datetime import date        

        iteration = _get_iteration(self.project_id, date(2008,07,26))
        self.assertEqual(iteration.id, 2)
        self.assertEqual(iteration.name, 'Iteration 1')


class TestUserStoryURLs(TestURLs, test.TestCase):

    def setUp(self):
        super(TestUserStoryURLs, self).setUp()        
        self._class = UserStory

class TestTestResultURLs(TestURLs, test.TestCase):
    
    def setUp(self):
        super(TestTestResultURLs, self).setUp()
        self._class = TestResult

    def test_testresult_absolute_view_retrieves_right_testresult(self):
        obj = TestResult.objects.all()[0]
        self.login()
        response = self.client.get(obj.get_absolute_url())           
        self.assertEqual(response.status_code, 200)
        self.assertEqual(obj.id, response.context[0]['object'].id)

    def test_testresult_simple_add(self):
        from datetime import date
        a_test_case = TestCase.objects.all()[0]
        pre = a_test_case.testresult_set.all().count()
        self.login()
        url = '/%s/userstory/%d/testcase/%d/testresult/add/' % ( a_test_case.user_story.project.id,
                                                                       a_test_case.user_story.id,
                                                                       a_test_case.id)
        self.login()
        context = { 'tester' : User.objects.get(pk=1).id,
                    'date': date(2008, 07, 31),
                    'result' : 1,
                    'test_case' : a_test_case.id }        
        response = self.client.post(url, context)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(a_test_case.testresult_set.all().count(), pre+1)

    def test_testresult_simple_edit(self):
        from datetime import date, datetime
        a_testresult = TestResult.objects.all()[0]
        self.login()
        url = '/%s/userstory/%d/testcase/%d/testresult/%d/edit/' %\
            (a_testresult.test_case.user_story.project.id,
             a_testresult.test_case.user_story.id,
             a_testresult.test_case.id, a_testresult.id)

        self.login()
        context = { 'tester' : User.objects.get(pk=1).id,
                    'date': date(2008, 07, 31),
                    'result' : 1,
                    'test_case' : a_testresult.test_case.id }        

        response = self.client.post(url, context)
        self.assertEqual(response.status_code, 302)
        a_testresult = TestResult.objects.get(pk=a_testresult.id)
        self.assertEqual(a_testresult.date, datetime(2008, 7, 31, 0, 0))
        self.assertEqual(a_testresult.result, 1)
        self.assertEqual(a_testresult.tester, User.objects.get(pk=1))

    def test_testresult_delete_simple(self):
        a_testresult = TestResult.objects.all()[0]
        pre = TestResult.objects.all().count()

        self.login()
        url = '/%s/userstory/%d/testcase/%d/testresult/%d/delete/' %\
            (a_testresult.test_case.user_story.project.id,
             a_testresult.test_case.user_story.id,
             a_testresult.test_case.id, a_testresult.id)

        self.login()
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(TestResult.objects.all().count(), pre-1)


class TestsForPageExistence:

    def test_exists(self):
        client = Client()
        response = client.get(self.page)
        self.assertNotEqual(response.status_code, 404)

class TestGetContainerModel(test.TestCase):
    fixtures = ['database_dump.json']

    # Project is a special case
    models = [Release, 
              Iteration, 
              UserStory, 
              Task, 
              TestCase, 
              TestResult,
              TaskLog]    
    
    def test_get_container_model_exists(self):
        for m in self.models:
            self.assert_(hasattr(m, 'get_container_model'))
        self.assert_(hasattr(Project, 'get_container_model'))
        
    def test_get_container_url_exists(self):
        for m, k in zip(self.models, xrange(len(self.models))):
            self.assert_(hasattr(m, 'get_container_url'), "Failed %d" % k)
        self.assert_(hasattr(Project, 'get_container_url'))

    def test_get_container_url_simple(self):
        for m, k in zip(self.models, xrange(len(self.models))):
            instance = m.objects.all()[0]
            self.assert_(instance.get_container_url(), "Failed %d" % k)
 
    def test_get_container_model_for_project_raises_exception(self):
        instance = Project.objects.all()[0]
        self.assertRaises(NotImplementedError, instance.get_container_model)

    def test_get_container_url_for_project_raises_exception(self):
        instance = Project.objects.all()[0]
        self.assertRaises(NotImplementedError, instance.get_container_url)

class Stylesheet(test.TestCase, TestsForPageExistence):
    page = '/resources/css/style.css'


class TestTimelog(test.TestCase, TTW):
    fixtures = ['burndown.json']
    username=password='admin'
    def test_tasklog_tracks_old_estimate(self):
        task = Task.objects.all().get()
        old_remaining = task.remaining
        self.login()
        context = dict(task='a%d' % task.id,
                       state=20,
                       estimate=task.estimate,
                       remaining=99,
                       time_on_task=1,
                       actuals=task.actuals,
                       summary='...',
                       date=datetime.date(2008,8,5))
        response = self.client.post('/log/', context)
        self.assertEqual(response.status_code, 200)
        log = TaskLog.objects.all().get()
        self.assertEqual(log.old_remaining, old_remaining)

    def test_burndown(self):
        it = Iteration.objects.all().get()
        self.login()
        response = self.client.get(it.get_absolute_url() + 'burndown_data/')
        self.assertEqual(response.status_code, 200)

class UserStory182(test.TestCase, TTW):
    fixtures = ['burndown.json']
    username=password='blah'
    def setUp(self):
        super(UserStory182, self).setUp()
        self.user = User(username=self.username)
        self.user.set_password(self.password)
        self.user.save()
        self.login()
    def testRestrictedThrows404(self):
        it = Iteration.objects.all()[0]
        response = self.client.get(it.get_absolute_url())
        self.assertEqual(response.status_code, 404)
        # I could check the text, but I don't think it helps any...

class TestAddAttachmentToUserStory(test.TestCase, TTW):
    fixtures = ['database_dump.json']
    
    def test_add_attachemt_to_user_story(self):
        from ifpeople_instance.settings import MEDIA_ROOT
        import os
        from os.path import dirname, join


        path = join(join(dirname(dirname(__file__)), 'media/'), 'ifpeople_logo-en.png')
        f = open(path, 'r')

        pre = UserStoryAttachment.objects.all().count()        
        story = UserStory.objects.filter().order_by('?')[0]
        story.project.project_members.add(User.objects.get(username=self.username))
        url = story.get_absolute_url() 
        self.login()
    
        context = dict(name='Test',
                       description='Test Attachment',
                       attachment=f,
                       user_story=story.id,
                       http_referer=url)

        response = self.client.post(url+'attachment/add/', context)
        f.close()        
        self.assertEqual(response.status_code, 302)        
 
        self.assertEqual(UserStoryAttachment.objects.all().count(), pre+1)
        
        # refres story
        story = UserStory.objects.get(id=story.id)
        us_attachment = story.userstoryattachment_set.filter(name='Test').get()
        self.assertEqual(us_attachment.attachment.name, 'attachments/ifpeople_logo-en.png')    
        response = self.client.get(us_attachment.attachment.url)
        self.assertEqual(response.status_code, 200)

        us_attachment.delete()
   
class TestDownloadingTimeLogsInCSVFormat(test.TestCase, TTW):
    fixtures = ['database_dump.json']

    def _check_rows(self, content, tl_qset):
        import csv
        import StringIO

        buf = StringIO.StringIO(content)
        reader = csv.reader(buf)

        num_rows1 = 0
        reader.next()
        for row in reader:
            num_rows1 += 1
        num_rows2 = tl_qset.count()
        self.assertEqual(num_rows1, num_rows2)        

        buf.seek(0)
        
        
        # skip first
        header = reader.next()
        self.assertEqual(header, ['Date','Project','Iteration','User Story',
                                  'Task','User','Time on Task','Summary'])
        for row, tl in zip(reader, tl_qset):
            tl_row = [("%s" % item) for item in tl.get_csv_row()]            
            self.assertEqual(row, tl_row)
    
    def test_csv_log_for_project(self):
        self.login()
        response = self.client.get('/1/csv/')
        self.assertEqual(response.status_code, 200)

        tl_set = TaskLog.objects.filter(task__user_story__project__pk=1).order_by('date', 'owner')

        splitted_content = self._check_rows(response.content, tl_set)

    def test_of_csv_log_for_project_with_dates(self):
        import datetime        

        self.login()
        response = self.client.get('/1/csv/', 
                                   { 'from_date' : datetime.date(2008,07,14),
                                     'to_date' : datetime.date(2008,07,17), 
                                   })
        self.assertEqual(response.status_code, 200)

        tl_set = TaskLog.objects.filter(task__user_story__project__pk=1,
                                        date__gte=datetime.date(2008,07,14),
                                        date__lte=datetime.date(2008,07,17)).order_by('date', 'owner')

        splitted_content = self._check_rows(response.content, tl_set)

    def test_csv_log_for_project_with_dates_for_specific_user(self):
        import datetime        

        self.login()
        response = self.client.get('/1/csv/alep/', 
                                   { 'from_date' : datetime.date(2008,07,14),
                                     'to_date' : datetime.date(2008,07,17), 
                                   })
        self.assertEqual(response.status_code, 200)

        tl_set = TaskLog.objects.filter(task__user_story__project__pk=1,
                                        date__gte=datetime.date(2008,07,14),
                                        date__lte=datetime.date(2008,07,17),
                                        owner=User.objects.get(username="alep")).order_by('date')

        splitted_content = self._check_rows(response.content, tl_set)

    def test_csv_log_for_all_projects(self):
        self.login()
        response = self.client.get('/csv/')
        self.assertEqual(response.status_code, 200)

        tl_set = TaskLog.objects.filter().order_by('date', 'owner')

        splitted_content = self._check_rows(response.content, tl_set)

    def test_csv_log_for_all_projects_with_dates(self):
        self.login()
        response = self.client.get('/csv/',
                                   { 'from_date' : datetime.date(2008,07,14),
                                     'to_date' : datetime.date(2008,07,17), 
                                   })
        self.assertEqual(response.status_code, 200)

        tl_set = TaskLog.objects.filter(date__gte=datetime.date(2008,07,14),
                                        date__lte=datetime.date(2008,07,17)
                                       ).order_by('date', 'owner')

        splitted_content = self._check_rows(response.content, tl_set)

class TestGetCsvRowMethod(test.TestCase):
    fixtures = ['database_dump.json']

    def test_get_csv_row_does_not_throw_exception(self):
        tl_set = TaskLog.objects.all()

        for tl in tl_set:
            self.assert_(tl.get_csv_row())

            pr = tl.task.user_story.project.name.encode('utf8')
            it = tl.task.user_story.iteration

            row = [tl.date, '%s' % pr,
                    '%s' % _if_is_none_else(it, 'Backlog', lambda x : x.name.encode('utf8')),
                    '%s' % tl.task.user_story.name.encode('utf8'),
                    '%s' % tl.task.name.encode('utf8'),
                    tl.owner.username,
                    tl.time_on_task,
                    '%s' % tl.summary.encode('utf8')]

            self.assertEqual(tl.get_csv_row(), row)
