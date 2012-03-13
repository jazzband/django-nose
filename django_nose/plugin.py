import os.path
import sys

from nose.plugins.base import Plugin

from django.conf import settings
from django.db.models.loading import get_apps, load_app
from django.test.testcases import TransactionTestCase


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
    """
    Captures the TestResult object for later inspection.

    nose doesn't return the full test result object from any of its runner
    methods.  Pass an instance of this plugin to the TestProgram and use
    ``result`` after running the tests to get the TestResult object.
    """

    name = "result"

    def finalize(self, result):
        self.result = result


class DjangoSetUpPlugin(AlwaysOnPlugin):
    """
    Configures Django to setup and tear down the environment.
    This allows coverage to report on all code imported and used during the
    initialisation of the test runner.

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
