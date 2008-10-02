from us49 import TestUS49Base
from agilito.models import UserStoryAttachment, UserStory 
from base import BASE_URL

class TestUS236(TestUS49Base):

    def test_add_an_attachment_to_us(self):
        from os.path import dirname, join
        path = join(join(dirname(dirname(dirname(__file__))), 'media/'), 'ifpeople_logo-en.png')

        pre = UserStoryAttachment.objects.all().count()

        b = self.browser
        b.click("link=Iteration")
        b.wait()

        b.click("link=ABC")
        b.wait()        
    
        last_location = b.get_location()
        b.click("link=add an attachment")
        b.wait()

        b.type("id_name", "A sample attachment")
        b.type("id_description", "This is an attachment hooray")
        b.type("id_attachment", path)
        b.click("xpath=id('content')/form/input")
        b.wait()
        
        location = b.get_location()
        self.assertEqual(location, last_location)
        self.assertEqual(pre+1, UserStoryAttachment.objects.all().count())

    def test_add_an_attachment_to_us_from_link(self):
        from os.path import dirname, join
        path = join(join(dirname(dirname(dirname(__file__))), 'media/'), 'ifpeople_logo-en.png')

        pre = UserStoryAttachment.objects.all().count()

        b = self.browser
        b.open(BASE_URL+"1/userstory/1/attachment/add")
        b.wait()

        b.type("id_name", "A sample attachment")
        b.type("id_description", "This is an attachment hooray")
        b.type("id_attachment", path)
        b.click("xpath=id('content')/form/input")
        b.wait()

        self.assertEqual(pre+1, UserStoryAttachment.objects.all().count())
        self.assertEqual(BASE_URL+"1/userstory/1/", b.get_location())


    def test_add_andthen_delete_attachment_using_urls(self):
        ####  by urls I mean writing the url on the address bar.
        from os.path import dirname, join
        path = join(join(dirname(dirname(dirname(__file__))), 'media/'), 'ifpeople_logo-en.png')

        pre = UserStoryAttachment.objects.all().count()

        b = self.browser
        b.open(BASE_URL+"1/userstory/1/attachment/add")
        b.wait()

        b.type("id_name", "A sample attachment")
        b.type("id_description", "This is an attachment hooray")
        b.type("id_attachment", path)
        b.click("xpath=id('content')/form/input")
        b.wait()

        self.assertEqual(pre+1, UserStoryAttachment.objects.all().count())
        self.assertEqual(BASE_URL+"1/userstory/1/", b.get_location())
        
        ## and now delete!

        pre = UserStoryAttachment.objects.all().count()
        usa = self.story.userstoryattachment_set.all()[0]

        b = self.browser
        b.open(BASE_URL+("1/userstory/1/attachment/%d/delete" % usa.id))
        b.wait()

        b.click("xpath=id('content')/form/div/input[2]")      
        b.wait()

        self.assertEqual(pre-1, UserStoryAttachment.objects.all().count())
        self.assertEqual(BASE_URL+"1/userstory/1/", b.get_location())

    def test_add_andthen_delete_attachment_clicking_on_view(self):
        from os.path import dirname, join
        path = join(join(dirname(dirname(dirname(__file__))), 'media/'), 'ifpeople_logo-en.png')

        pre = UserStoryAttachment.objects.all().count()

        b = self.browser
        b.click("link=Iteration")
        b.wait()

        b.click("link=ABC")
        b.wait()        
    
        last_location = b.get_location()
        b.click("link=add an attachment")
        b.wait()

        b.type("id_name", "A sample attachment")
        b.type("id_description", "This is an attachment hooray")
        b.type("id_attachment", path)
        b.click("xpath=id('content')/form/input")
        for x in xrange(100):
            b.wait()
        
        self.assertEqual(b.get_location(), last_location)
        self.assertEqual(pre+1, UserStoryAttachment.objects.all().count())

        ## and now delete it
        last_location = b.get_location()

        pre = UserStoryAttachment.objects.all().count()
        b.click("xpath=id('att_del')/img")
        b.wait()

        b.click("xpath=id('content')/form/div/input[2]")      
        b.wait()

        self.assertEqual(b.get_location(), last_location)
        self.assertEqual(pre-1, UserStoryAttachment.objects.all().count())

    def test_add_andthen_download_attachment_clicking_on_view(self):
        from os.path import dirname, join
        path = join(join(dirname(dirname(dirname(__file__))), 'media/'), 'ifpeople_logo-en.png')

        pre = UserStoryAttachment.objects.all().count()

        b = self.browser
        b.click("link=Iteration")
        b.wait()

        b.click("link=ABC")
        b.wait()        
    
        last_location = b.get_location()
        b.click("link=add an attachment")
        b.wait()

        b.type("id_name", "A sample attachment")
        b.type("id_description", "This is an attachment hooray")
        b.type("id_attachment", path)
        b.click("xpath=id('content')/form/input")
        for x in xrange(10):
            b.wait()
        
        self.assertEqual(b.get_location(), last_location)
        self.assertEqual(pre+1, UserStoryAttachment.objects.all().count())

        ### and now download it
        b.click("xpath=id('att_dwld')/img")
        b.wait()
        b.choose_ok_on_next_confirmation()
        usa = self.story.userstoryattachment_set.all()[0]
        self.assertEqual(BASE_URL+usa.attachment.url[1:], b.get_location())

        ### return to main screen
        b.open(BASE_URL)

