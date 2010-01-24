"""
Django test runner that invokes nose.

You can use

    NOSE_ARGS = ['list', 'of', 'args']

in settings.py for arguments that you always want passed to nose.
"""
import os
import sys

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.models import get_apps
from django.test.simple import DjangoTestSuiteRunner, get_tests

import nose.core

from django_nose.plugin import ResultPlugin

try:
    any
except NameError:
    def any(iterable):
        for element in iterable:
            if element:
                return True
        return False

# This is a table of Django's "manage.py test" options which
# correspond to nosetests options with a different name:
OPTION_TRANSLATION = {'--failfast': '-x'}

class NoseTestSuiteRunner(DjangoTestSuiteRunner):
    def run_suite(self, nose_argv):
        result_plugin = ResultPlugin()
        nose.core.TestProgram(argv=nose_argv, exit=False,
                              addplugins=[result_plugin])
        return result_plugin.result

    def build_suite(self):
        """Unused method

        The build_suite() method of django.test.simple.DjangoTestSuiteRunner is
        not used in django_nose.
        """
        pass

    def run_tests(self, test_labels, extra_tests=None):
        """
        Run the unit tests for all the test names in the provided list.

        Test names specified may be file or module names, and may optionally
        indicate the test case to run by separating the module or file name from
        the test case name with a colon. Filenames may be relative or
        absolute. Examples:

        runner.run_tests('test.module')
        runner.run_tests('another.test:TestCase.test_method')
        runner.run_tests('a.test:TestCase')
        runner.run_tests('/path/to/test/file.py:test_function')

        Returns the number of tests that failed.
        """
        self.setup_test_environment()
        for app in get_apps():
            # register models from .tests modules in apps
            get_tests(app)
        old_names = self.setup_databases()

        nose_argv = ['nosetests']
        if hasattr(settings, 'NOSE_ARGS'):
            nose_argv.extend(settings.NOSE_ARGS)

        # Skip over 'manage.py test' and any arguments handled by django.
        django_opts = ['--noinput']
        for opt in BaseCommand.option_list:
            django_opts.extend(opt._long_opts)
            django_opts.extend(opt._short_opts)

        nose_argv.extend(OPTION_TRANSLATION.get(opt, opt)
                         for opt in sys.argv[2:]
                         if not any(opt.startswith(d) for d in django_opts))

        if self.verbosity >= 1:
            print ' '.join(nose_argv)

        result = self.run_suite(nose_argv)
        self.teardown_databases(old_names)
        self.teardown_test_environment()
        return self.suite_result(result)

def _get_options():
    """Return all nose options that don't conflict with django options."""
    cfg_files = nose.core.all_config_files()
    manager = nose.core.DefaultPluginManager()
    config = nose.core.Config(env=os.environ, files=cfg_files, plugins=manager)
    options = config.getParser().option_list
    django_opts = [opt.dest for opt in BaseCommand.option_list] + ['version']
    return tuple(o for o in options if o.dest not in django_opts and
                                       o.action != 'help')


# Replace the builtin command options with the merged django/nose options.
NoseTestSuiteRunner.options = _get_options()
NoseTestSuiteRunner.__test__ = False
