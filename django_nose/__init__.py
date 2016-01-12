# coding: utf-8
"""The django_nose module."""
from __future__ import unicode_literals

from django_nose.runner import BasicNoseRunner, NoseTestSuiteRunner
from django_nose.testcases import FastFixtureTestCase
assert BasicNoseRunner
assert FastFixtureTestCase

VERSION = (1, 4, 3)
__version__ = '.'.join(map(str, VERSION))
run_tests = run_gis_tests = NoseTestSuiteRunner


# Replace the default test loader.
import django_nose.loader