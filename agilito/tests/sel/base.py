import unittest
import selenium
import random

from django.db.backends.creation import TEST_DATABASE_PREFIX
from django.conf import settings
settings.DATABASE_NAME = settings.TEST_DATABASE_NAME \
    or TEST_DATABASE_PREFIX + settings.DATABASE_NAME

HOST = getattr(settings, 'SELENIUM_HOST', 'localhost')
PORT = getattr(settings, 'SELENIUM_PORT', 4444)
BROWSER = getattr(settings, 'SELENIUM_BROWSER', '*firefox')
BASE_URL = getattr(settings, 'SELENIUM_BASE_URL', 'http://localhost:8000/')
SPEED = getattr(settings, 'SELENIUM_SPEED', None)
WAIT_TIME = getattr(settings, 'SELENIUM_WAIT_TIME', 15000)

class my_selenium(selenium.selenium):
    def __init__(self):
        selenium.selenium.__init__(self, HOST, PORT, BROWSER, BASE_URL)
    def wait(self):
        return self.wait_for_page_to_load(WAIT_TIME)

def random_name():
    return ''.join(chr(random.randint(ord('a'), ord('z'))) for i in range(10))

class SeleniumBase(unittest.TestCase):
    do_login = True
    do_logout = True
    do_stop_browser = True
    def setUp(self):
        self.browser = my_selenium()
        self.browser.start()
        if SPEED is not None:
            self.browser.set_speed(SPEED)
        if self.do_login:
            self.login()
    def tearDown(self):
        if self.do_logout:
            self.logout()
        if self.do_stop_browser:
            self.browser.stop()

    def login(self, username=None, password=None):
        b = self.browser
        b.open('/accounts/login/?next=/')
        b.type('id_username', username or self.user.username)
        b.type('id_password', password or self.passwd)
        b.click("//input[@value='login']")
        b.wait()

    def logout(self):
        self.browser.click('link=Sign out')
        self.browser.wait()


