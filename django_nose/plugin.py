import os.path
import sys

from django.conf import settings
from django.db import connections, router
from django.db.models import signals
from django.db.models.loading import get_apps, get_models, load_app

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
        self.sys_stderr = sys.stderr

    def begin(self):
        self.started = False
        self.add_apps = set()

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

    def beforeTest(self, test):
        if self.started:
            return

        self.started = True

        if self.add_apps:
            settings.INSTALLED_APPS = set(settings.INSTALLED_APPS)
            for app in self.add_apps:
                mod = load_app(app)
                if mod:
                    settings.INSTALLED_APPS.add(app)
            settings.INSTALLED_APPS = tuple(settings.INSTALLED_APPS)

        sys_stdout = sys.stdout
        sys_stderr = sys.stderr
        sys.stdout = self.sys_stdout
        sys.stderr = self.sys_stderr

        get_apps()

        self.runner.setup_test_environment()

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

        sys.stdout = sys_stdout
        sys.stderr = sys_stderr

    def finalize(self, result):
        if self.started and hasattr(self, 'old_names'):
            self.runner.teardown_databases(self.old_names)
            self.runner.teardown_test_environment()
