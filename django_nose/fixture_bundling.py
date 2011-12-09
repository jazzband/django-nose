from nose.plugins import Plugin
from nose.suite import ContextSuite


class Bucketer(object):
    def __init__(self):
        # { frozenset(['users.json']):
        #      [ContextSuite(...), ContextSuite(...)] }
        self.buckets = {}

    def add(self, test):
        """Put a test into a bucket according to its set of fixtures and the
        value of its exempt_from_fixture_bundling attr."""
        key = (frozenset(getattr(test.context, 'fixtures', [])),
               getattr(test.context, 'exempt_from_fixture_bundling', False))
        self.buckets.setdefault(key, []).append(test)


class FixtureBundlingPlugin(Plugin):
    """Nose plugin which reorders tests to avoid redundant fixture setup

    I reorder test classes so ones using identical sets of fixtures run
    adjacently. I then put attributes on the classes which advise a savvy
    test superclass (like test-utils' FastFixtureTestCase) to not reload the
    fixtures for each class.

    This takes support.mozilla.com's suite from 123s down to 94s.

    """
    name = 'fixture-bundling'

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
            if (not hasattr(suite, '_tests') or
                (hasattr(suite, 'hasFixtures') and suite.hasFixtures())):
                # We hit a Test or something with setup, so do the thing.
                base_callable(suite)
            else:
                for t in suite._tests:
                    process_tests(t, base_callable)

        def suite_sorted_by_fixtures(suite):
            """Flatten and sort a tree of Suites by the ``fixtures`` members of
            their contexts.

            Add ``_fb_should_setup_fixtures`` and
            ``_fb_should_teardown_fixtures`` attrs to each test class to advise
            it whether to set up or tear down (respectively) the fixtures.

            Return a Suite.

            """
            bucketer = Bucketer()
            process_tests(suite, bucketer.add)

            # Lay the bundles of common-fixture-having test classes end to end
            # in a single list so we can make a test suite out of them:
            flattened = []
            for ((fixtures, is_exempt), fixture_bundle) in bucketer.buckets.iteritems():
                # Advise first and last test classes in each bundle to set up
                # and tear down fixtures and the rest not to:
                if fixtures and not is_exempt:
                    # Ones with fixtures are sure to be classes, which means
                    # they're sure to be ContextSuites with contexts.

                    # First class with this set of fixtures sets up:
                    fixture_bundle[0].context._fb_should_setup_fixtures = True

                    # Set all classes' 1..n should_setup to False:
                    for cls in fixture_bundle[1:]:
                        cls.context._fb_should_setup_fixtures = False

                    # Last class tears down:
                    fixture_bundle[-1].context._fb_should_teardown_fixtures = True

                    # Set all classes' 0..(n-1) should_teardown to False:
                    for cls in fixture_bundle[:-1]:
                        cls.context._fb_should_teardown_fixtures = False

                flattened.extend(fixture_bundle)

            return ContextSuite(flattened)

        return suite_sorted_by_fixtures(test)
