import sys

from nose.suite import ContextSuite


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
        """Setup the environment"""
        sys_stdout = sys.stdout
        sys.stdout = self.sys_stdout

        self.runner.setup_test_environment()
        self.old_names = self.runner.setup_databases()

        sys.stdout = sys_stdout

    def prepareTest(self, test):
        """Reorder the tests in the suite so classes using identical sets of
        fixtures are contiguous."""
        def process_tests(suite, base_callable):
            """Given a nested disaster of [Lazy]Suites, traverse to the first
            level that has setup or teardown routines, and do something to
            them.

            If we were to traverse all the way to the leaves (the Tests)
            indiscriminately and return them, when the runner later calls them,
            they'd run without reference to the suite that contained them, so
            they'd miss their class-, module-, and package-wide setup and
            teardown routines.

            The nested suites form basically a double-linked tree, and suites
            will call up to their containing suites to run their setups and
            teardowns, but it would be hubris to assume that something you saw
            fit to setup or teardown at the module level is less costly to
            repeat than DB fixtures. Also, those sorts of setups and teardowns
            are extremely rare in our code. Thus, we limit the granularity of
            bucketing to the first level that has setups or teardowns.

            """
            if not hasattr(suite, '_tests') or (hasattr(suite, 'hasFixtures') and suite.hasFixtures()):
                # We hit a Test or something with setup, so do the thing.
                base_callable(suite)
            else:
                for t in suite._tests:
                    process_tests(t, base_callable)

        class Bucketer(object):
            def __init__(self):
                # { frozenset(['users.json']):
                #      [ContextSuite(...), ContextSuite(...)] }
                self.buckets = {}

            def add(self, test):
                fixtures = frozenset(getattr(test.context, 'fixtures', []))
                self.buckets.setdefault(fixtures, []).append(test)

        def suite_sorted_by_fixtures(suite):
            """Flatten and sort a tree of Suites by the ``fixtures`` members of
            their contexts.

            Add ``_fg_should_setup_fixtures`` and
            ``_fg_should_teardown_fixtures`` attrs to each test class to advise
            it whether to set up or tear down (respectively) the fixtures.

            Return a Suite.

            """
            bucketer = Bucketer()
            process_tests(suite, bucketer.add)

            # Lay the bundles of common-fixture-having test classes end to end
            # in a single list so we can make a test suite out of them:
            flattened = []
            for (key, fixture_bundle) in bucketer.buckets.iteritems():
                # Advise first and last test classes in each bundle to set up
                # and tear down fixtures and the rest not to:
                if key:  # Ones with fixtures are sure to be classes, which
                         # means they're sure to be ContextSuites with
                         # contexts.
                    # First class with this set of fixtures sets up:
                    fixture_bundle[0].context._fg_should_setup_fixtures = True

                    # Set all classes' 1..n should_setup to False:
                    for cls in fixture_bundle[1:]:
                        cls.context._fg_should_setup_fixtures = False

                    # Last class tears down:
                    fixture_bundle[-1].context._fg_should_teardown_fixtures = True

                    # Set all classes' 0..(n-1) should_teardown to False:
                    for cls in fixture_bundle[:-1]:
                        cls.context._fg_should_teardown_fixtures = False

                flattened.extend(fixture_bundle)

            return ContextSuite(flattened)

        return suite_sorted_by_fixtures(test)

    def finalize(self, result):
        """Destroy the environment"""
        self.runner.teardown_databases(self.old_names)
        self.runner.teardown_test_environment()
