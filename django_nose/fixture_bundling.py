from nose.plugins import Plugin
from nose.suite import ContextSuite

from django_nose.utils import process_tests


class Bucketer(object):
    def __init__(self):
        # { (frozenset(['users.json']), True):
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
    score = 100  # For relationship with TransactionTestReorderer

    def prepareTest(self, test):
        """Reorder the tests in the suite so classes using identical sets of
        fixtures are contiguous."""

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
