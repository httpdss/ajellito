from us49 import TestUS49Base
from base import BASE_URL
from agilito.models import Task
import re

class TestUS121(TestUS49Base):
    
    def test_simple(self):
        """
        Just checks if I really deleted the task
        """

        b = self.browser
        b.wait()
        location = b.get_location()
        text = b.get_text("xpath=//h2") 
            

        # I don't know what is the id of the project.
        # So I use regular expresion to match the text
        re_url = re.compile(r'\d/iteration/')
        m = re_url.match(location, len(BASE_URL))        
        self.assert_(not (m is None))
        
        # But anyway lets just check the url
        self.assertEqual(m.group(0), '1/iteration/')

