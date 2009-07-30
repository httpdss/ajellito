import unittest, os, sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

projectdir = os.path.abspath(os.path.dirname(__file__))
while projectdir != '/' and not os.path.exists(os.path.join(projectdir, 'settings.py')):
    projectdir = os.path.dirname(projectdir)
if projectdir != '/':
    sys.path.append(projectdir)

from django.test import _doctest as doctest
from django.test.testcases import OutputChecker, DocTestRunner

# take care to add modules to two separate places:
# import the individual tests so asking for one specific testrun works
from ttw import *
from unit import *
from doc import *

def suite():
    doctestOutputChecker = OutputChecker()
    suite = unittest.TestSuite()
    # import the modules so I can add them piecemeal to the suite
    import ttw, unit, doc

    for module in ttw, unit:
        suite.addTest(unittest.defaultTestLoader.loadTestsFromModule(module))
    for module in doc, :
        suite.addTest(doctest.DocTestSuite(module, 
                                           checker=doctestOutputChecker,
                                           runner=DocTestRunner))
    return suite

