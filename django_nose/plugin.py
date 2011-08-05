import os.path
import sys

from django.conf import settings
from django.db import connections, router
from django.db.models import signals
from django.db.models.loading import get_apps, get_models, load_app
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

class _EmptyClass(object):
    pass

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
        self.sys_stderr = sys.stderr
        self.needs_db = False
        self.started = False

    def begin(self):
        self.add_apps = set()

    def wantClass(self, cls):
        if issubclass(cls, TransactionTestCase):
            self.needs_db = True

    def wantMethod(self, method):
        if issubclass(method.im_class, TransactionTestCase):
            self.needs_db = True

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
            settings.INSTALLED_APPS = set(settings.INSTALLED_APPS)
            for app in self.add_apps:
                mod = load_app(app)
                if mod:
                    settings.INSTALLED_APPS.add(app)
            settings.INSTALLED_APPS = tuple(settings.INSTALLED_APPS)

        get_apps()

        self.runner.setup_test_environment()

        if self.needs_db:
            # HACK: We need to kill post_syncdb receivers to stop them from sending when the databases
            #       arent fully ready.
            post_syncdb_receivers = signals.post_syncdb.receivers
            signals.post_syncdb.receivers = []
            self.old_names = self.runner.setup_databases()
            signals.post_syncdb.receivers = post_syncdb_receivers

            for app in get_apps():
                app_models = list(get_models(app, include_auto_created=True))
                for db in connections:
                    all_models = [m for m in app_models if router.allow_syncdb(db, m)]
                    if not all_models:
                        continue
                    signals.post_syncdb.send(app=app, created_models=all_models, verbosity=self.runner.verbosity,
                                             db=db, sender=app, interactive=False)

        sys.stdout = cur_stdout
        sys.stderr = cur_stderr

        self.started = True

    def finalize(self, result):
        if self.started:
            if self.needs_db:
                self.runner.teardown_databases(self.old_names)
            
            self.runner.teardown_test_environment()