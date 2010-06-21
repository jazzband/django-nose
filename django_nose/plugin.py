

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

    def begin(self):
        """Setup the environment"""
        self.runner.setup_test_environment()
        self.old_names = self.runner.setup_databases()

    def finalize(self, result):
        """Destroy the environment"""
        self.runner.teardown_databases(self.old_names)
        self.runner.teardown_test_environment()
