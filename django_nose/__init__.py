# coding: utf-8
"""The django_nose module."""
from __future__ import unicode_literals

from django_nose.runner import BasicNoseRunner, NoseTestSuiteRunner
from django_nose.testcases import FastFixtureTestCase
assert BasicNoseRunner
assert FastFixtureTestCase

VERSION = (1, 4, 2)
__version__ = '.'.join(map(str, VERSION))

# Django < 1.2 compatibility.
run_tests = run_gis_tests = NoseTestSuiteRunner
