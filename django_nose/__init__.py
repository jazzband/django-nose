from __future__ import unicode_literals

VERSION = (1, 4, 0)
__version__ = '.'.join(map(str, VERSION))

from django_nose.runner import *
from django_nose.testcases import *


# Django < 1.2 compatibility.
run_tests = run_gis_tests = NoseTestSuiteRunner
