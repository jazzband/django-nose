import os.path
import sys

from django.conf import settings
from django.db.models.loading import get_apps, load_app
from django.test.testcases import TransactionTestCase


class ResultPlugin(object):
    """
    Captures the TestResult object for later inspection.

    nose doesn't return the full test result object from any of its runner
    methods.  Pass an instance of this plugin to the TestProgram and use
    ``result`` after running the tests to get the TestResult object.
    """

    name = "result"
    enabled = True

    def finalize(self, result):
        self.result = result



class DjangoSetUpPlugin(object):
    """
    Configures Django to setup and tear down the environment.
    This allows coverage to report on all code imported and used during the
    initialisation of the test runner.

    """
    name = "django setup"
    enabled = True

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


# TODO: Moving this out of the main plugin because it's causing issues like #41
# and won't let you run something like
# `manage.py test apps/webapps/tests/test_models.py`. The plugin isn't
# functional in this state but should be rewritten to cooperate with other
# plugins rather than being embedded inside the main plugin (if possible).
# It was functional as of
# https://github.com/jbalogh/django-nose/blob/8d8498b/django_nose/plugin.py
class XXPlugin(object):
    """
    Only sets up databases if a single class inherits from
    ``django.test.testcases.TransactionTestCase``.

    Also ensures you don't run the same test case multiple times.
    """

    def __init__(self, runner):
        self.sys_stderr = sys.stderr
        self.needs_db = False
        self.started = False
        self._registry = set()

    def begin(self):
        self.add_apps = set()

    def wantClass(self, cls):
        if issubclass(cls, TransactionTestCase):
            self.needs_db = True

        if cls in self._registry:
            return False
        self._registry.add(cls)

    def wantMethod(self, method):
        if issubclass(method.im_class, TransactionTestCase):
            self.needs_db = True

        if method in self._registry:
            return False
        self._registry.add(method)

    def wantFunction(self, function):
        if function in self._registry:
            return False
        self._registry.add(function)

    def beforeImport(self, filename, module):
        # handle case of tests.models
        if not os.path.isdir(filename):
            filepath = os.path.dirname(filename)
            module = module.rsplit('.', 1)[0]
        else:
            filepath = filename

        models_path = os.path.join(filepath, 'models.py')
        if os.path.exists(models_path):
            self.add_apps.add(module)

        # handle case of fooapp.tests, where fooapp.models exists
        models_path = os.path.join(filepath, os.pardir, 'models.py')
        if os.path.exists(models_path):
            self.add_apps.add(module.rsplit('.', 1)[0])

    def prepareTestRunner(self, test):
        cur_stdout = sys.stdout
        cur_stderr = sys.stderr

        sys.stdout = self.sys_stdout
        sys.stderr = self.sys_stderr

        if self.add_apps:
            for app in self.add_apps:
                if app in settings.INSTALLED_APPS:
                    continue
                mod = load_app(app)
                if mod:
                    settings.INSTALLED_APPS.append(app)

        get_apps()

        self.runner.setup_test_environment()

        if self.needs_db:
            self.old_names = self.runner.setup_databases()

        sys.stdout = cur_stdout
        sys.stderr = cur_stderr

        self.started = True

    def finalize(self, result):
        if self.started:
            if self.needs_db:
                self.runner.teardown_databases(self.old_names)

            self.runner.teardown_test_environment()
