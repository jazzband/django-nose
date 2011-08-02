import os.path
import sys
import unittest

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

def make_django_runner(parent, runner, sys_stdout, sys_stderr, add_apps):
    """
    Creates a test runner which only sets up databases if the test case class
    inherits from django.test.TestCase
    """
    if add_apps:
        settings.INSTALLED_APPS = set(settings.INSTALLED_APPS)
        for app in add_apps:
            mod = load_app(app)
            if mod:
                settings.INSTALLED_APPS.add(app)
        settings.INSTALLED_APPS = tuple(settings.INSTALLED_APPS)

    class DatabaselessTestRunner(parent.__class__):
        def run(self, test):
            needs_db = False
            context_list = list(test._tests)
            while context_list:
                context = context_list.pop()
                if isinstance(context, unittest.TestCase):
                    if isinstance(context.test, TransactionTestCase):
                        needs_db = True
                    continue
                else:
                    context_list.extend(context)
            
            cur_stdout = sys.stdout
            cur_stderr = sys.stderr

            sys.stdout = sys_stdout
            sys.stderr = sys_stderr

            get_apps()

            runner.setup_test_environment()

            if needs_db:
                # HACK: We need to kill post_syncdb receivers to stop them from sending when the databases
                #       arent fully ready.
                post_syncdb_receivers = signals.post_syncdb.receivers
                signals.post_syncdb.receivers = []
                old_names = runner.setup_databases()
                signals.post_syncdb.receivers = post_syncdb_receivers

                for app in get_apps():
                    app_models = list(get_models(app, include_auto_created=True))
                    for db in connections:
                        all_models = [m for m in app_models if router.allow_syncdb(db, m)]
                        if not all_models:
                            continue
                        signals.post_syncdb.send(app=app, created_models=all_models, verbosity=runner.verbosity,
                                                 db=db, sender=app, interactive=False)

            sys.stdout = cur_stdout
            sys.stderr = cur_stderr

            result = super(DatabaselessTestRunner, self).run(test)

            if needs_db:
                runner.teardown_databases(old_names)
            
            runner.teardown_test_environment()

            return result

    inst = _EmptyClass()
    inst.__class__ = DatabaselessTestRunner
    inst.__dict__.update(parent.__dict__)
    return inst

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

    def prepareTestRunner(self, test):
        return make_django_runner(test, self.runner, self.sys_stdout, self.sys_stderr, self.add_apps)

