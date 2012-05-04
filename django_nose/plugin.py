import os.path
import sys

from nose.plugins.base import Plugin
from nose.suite import ContextSuite

from django.conf import settings
from django.db.models.loading import get_apps, load_app
from django.test.testcases import TransactionTestCase, TestCase

from django_nose.utils import process_tests, is_subclass_at_all


class AlwaysOnPlugin(Plugin):
    """A plugin that takes no options and is always enabled"""

    def options(self, parser, env):
        """Avoid adding a ``--with`` option for this plugin.

        We don't have any options, and this plugin is always enabled, so we
        don't want to use superclass's ``options()`` method which would add a
        ``--with-*`` option.

        """

    def configure(self, *args, **kw_args):
        super(AlwaysOnPlugin, self).configure(*args, **kw_args)
        self.enabled = True  # Force this plugin to be always enabled.


class ResultPlugin(AlwaysOnPlugin):
    """Captures the TestResult object for later inspection

    nose doesn't return the full test result object from any of its runner
    methods.  Pass an instance of this plugin to the TestProgram and use
    ``result`` after running the tests to get the TestResult object.

    """
    name = "result"

    def finalize(self, result):
        self.result = result


class DjangoSetUpPlugin(AlwaysOnPlugin):
    """Configures Django to set up and tear down the environment

    This allows coverage to report on all code imported and used during the
    initialization of the test runner.

    """
    name = "django setup"

    def __init__(self, runner):
        super(DjangoSetUpPlugin, self).__init__()
        self.runner = runner
        self.sys_stdout = sys.stdout

    def begin(self):
        sys_stdout = sys.stdout
        sys.stdout = self.sys_stdout

        self.runner.setup_test_environment()
        self.old_names = self.runner.setup_databases()

        sys.stdout = sys_stdout

    def finalize(self, result):
        self.runner.teardown_databases(self.old_names)
        self.runner.teardown_test_environment()


class TransactionTestReorderer(AlwaysOnPlugin):
    """Runs TransactionTestCase-based tests last

    Django has a weird design decision wherein TransactionTestCase doesn't
    clean up after itself. Instead, it resets the DB to a clean state only at
    the *beginning* of each test:
    https://docs.djangoproject.com/en/dev/topics/testing/?from=olddocs#django.
    test.TransactionTestCase. Thus, Django reorders tests so
    TransactionTestCases all come last. Here we do the same.

    "I think it's historical. We used to have doctests also, adding cleanup
    after each unit test wouldn't necessarily clean up after doctests, so you'd
    have to clean on entry to a test anyway." was once uttered on #django-dev.

    """
    name = 'transaction-test-reordering'

    # Come before fixture bundling. It probably doesn't matter, but they both
    # mess with test order, so why leave it to chance?
    score = 110

    def prepareTest(self, test):
        """Reorder tests in the suite so TransactionTestCase-based tests come last."""

        def filthiness(test):
            """Return a comparand based on whether a test is guessed to clean
            up after itself.

            Django's TransactionTestCase doesn't clean up the DB on teardown,
            but it's hard to guess whether subclasses (other than TestCase) do.
            We will assume they don't, unless they have a
            ``cleans_up_after_itself`` attr set to True. This is reasonable
            because the odd behavior of TransactionTestCase is documented, so
            subclasses should by default be assumed to preserve it.

            Thus, things will get these comparands (and run in this order):

            * 1: TestCase subclasses. These clean up after themselves.
            * 1: TransactionTestCase subclasses with
                 cleans_up_after_itself=True. These include
                 FastFixtureTestCases. If you're using the
                 FixtureBundlingPlugin, it will pull the FFTCs out, reorder
                 them, and run them first of all.
            * 2: TransactionTestCase subclasses. These leave a mess.
            * 2: Anything else (including doctests, I hope). These don't care
                 about the mess you left, because they don't hit the DB or, if
                 they do, are responsible for ensuring that it's clean (as per
                 https://docs.djangoproject.com/en/dev/topics/testing/?from=
                 olddocs#writing-doctests)

            """
            test_class = test.context
            if (is_subclass_at_all(test_class, TestCase) or
                (is_subclass_at_all(test_class, TransactionTestCase) and
                  getattr(test_class, 'cleans_up_after_itself', False))):
                return 1
            return 2

        flattened = []
        process_tests(test, flattened.append)
        flattened.sort(key=filthiness)
        return ContextSuite(flattened)
