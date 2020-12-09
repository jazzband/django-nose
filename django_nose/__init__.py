# coding: utf-8
"""The django_nose module."""
from pkg_resources import get_distribution, DistributionNotFound

from django_nose.runner import BasicNoseRunner, NoseTestSuiteRunner
from django_nose.testcases import FastFixtureTestCase

assert BasicNoseRunner
assert NoseTestSuiteRunner
assert FastFixtureTestCase

try:
    __version__ = get_distribution("django-nose").version
except DistributionNotFound:
    # package is not installed
    pass
