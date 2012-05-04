from nose.plugins import Plugin
from nose.suite import ContextSuite

from django_nose.testcases import FastFixtureTestCase
from django_nose.utils import process_tests, is_subclass_at_all


class Bucketer(object):
    def __init__(self):
        # { (frozenset(['users.json']), True):
        #      [ContextSuite(...), ContextSuite(...)] }
        self.buckets = {}

        # All the non-FastFixtureTestCase tests we saw, in the order they came
        # in:
        self.remainder = []

    def add(self, test):
        """Put a test into a bucket according to its set of fixtures and the
        value of its exempt_from_fixture_bundling attr."""
        if is_subclass_at_all(test, FastFixtureTestCase):
            # We bucket even FFTCs that don't have any fixtures, but it
            # shouldn't matter.
            key = (frozenset(getattr(test.context, 'fixtures', [])),
                   getattr(test.context, 'exempt_from_fixture_bundling', False))
            self.buckets.setdefault(key, []).append(test)
        else:
            self.remainder.append(test)


class FixtureBundlingPlugin(Plugin):
    """Nose plugin which reorders tests to avoid redundant fixture setup

    I reorder FastFixtureTestCases so ones using identical sets of fixtures run
    adjacently. I then put attributes on them to advise them to not reload the
    fixtures for each class.

    This takes support.mozilla.com's suite from 123s down to 94s.

    """
    name = 'fixture-bundling'
    score = 100  # For relationship with TransactionTestReorderer

    def prepareTest(self, test):
        """Reorder the tests in the suite so classes using identical sets of
        fixtures are contiguous.

        FastFixtureTestCases are the only ones we care about, because nobody
        else, in practice, pays attention to the ``_fb`` advisory bits. We
        return those first, then any remaining tests in the order they were
        received.

        """
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
            flattened.extend(bucketer.remainder)

            return ContextSuite(flattened)

        return suite_sorted_by_fixtures(test)
