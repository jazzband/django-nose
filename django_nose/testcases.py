import os
import sys

from django import test
from django.conf import settings
from django.core import cache, mail
from django.core.management import call_command
from django.db import connections, DEFAULT_DB_ALIAS, transaction
from django_nose.fixture_tables import tables_used_by_fixtures
from django_nose.utils import uses_mysql
from django.core.exceptions import ImproperlyConfigured
from django.test import LiveServerTestCase
from django.utils import six


__all__ = ['FastFixtureTestCase', 'FastFixtureLiveServerTestCase']


class FastFixtureTestCase(test.TransactionTestCase):
    """Test case that loads fixtures once and for all rather than once per test

    Using this can save huge swaths of time while still preserving test
    isolation. Fixture data is loaded at class setup time, and the transaction
    is committed. Commit and rollback methods are then monkeypatched away (like
    in Django's standard TestCase), and each test is run. After each test, the
    monkeypatching is temporarily undone, and a rollback is issued, returning
    the DB content to the pristine fixture state. Finally, upon class teardown,
    the DB is restored to a post-syncdb-like state by deleting the contents of
    any table that had been touched by a fixture (keeping infrastructure tables
    like django_content_type and auth_permission intact).

    Note that this is like Django's TestCase, not its TransactionTestCase, in
    that you cannot do your own commits or rollbacks from within tests.

    For best speed, group tests using the same fixtures into as few classes as
    possible. Better still, don't do that, and instead use the fixture-bundling
    plugin from django-nose, which does it dynamically at test time.

    """
    cleans_up_after_itself = True  # This is the good kind of puppy.

    @classmethod
    def setUpClass(cls):
        """Turn on manual commits. Load and commit the fixtures."""
        if not test.testcases.connections_support_transactions():
            raise NotImplementedError('%s supports only DBs with transaction '
                                      'capabilities.' % cls.__name__)
        for db in cls._databases():
            # These MUST be balanced with one leave_* each:
            transaction.enter_transaction_management(using=db)
            # Don't commit unless we say so:
            transaction.managed(True, using=db)

        cls._fixture_setup()

    @classmethod
    def tearDownClass(cls):
        """Truncate the world, and turn manual commit management back off."""
        cls._fixture_teardown()
        for db in cls._databases():
            # Finish off any transactions that may have happened in
            # tearDownClass in a child method.
            if transaction.is_dirty(using=db):
                transaction.commit(using=db)
            transaction.leave_transaction_management(using=db)

    @classmethod
    def _fixture_setup(cls):
        """Load fixture data, and commit."""
        for db in cls._databases():
            if (hasattr(cls, 'fixtures') and
                getattr(cls, '_fb_should_setup_fixtures', True)):
                # Iff the fixture-bundling test runner tells us we're the first
                # suite having these fixtures, set them up:
                call_command('loaddata', *cls.fixtures, **{'verbosity': 0,
                                                           'commit': False,
                                                           'database': db})
            # No matter what, to preserve the effect of cursor start-up
            # statements...
            transaction.commit(using=db)

    @classmethod
    def _fixture_teardown(cls):
        """Empty (only) the tables we loaded fixtures into, then commit."""
        if hasattr(cls, 'fixtures') and \
           getattr(cls, '_fb_should_teardown_fixtures', True):
            # If the fixture-bundling test runner advises us that the next test
            # suite is going to reuse these fixtures, don't tear them down.
            for db in cls._databases():
                tables = tables_used_by_fixtures(cls.fixtures, using=db)
                # TODO: Think about respecting _meta.db_tablespace, not just
                # db_table.
                if tables:
                    connection = connections[db]
                    cursor = connection.cursor()

                    # TODO: Rather than assuming that anything added to by a
                    # fixture can be emptied, remove only what the fixture
                    # added. This would probably solve input.mozilla.com's
                    # failures (since worked around) with Site objects; they
                    # were loading additional Sites with a fixture, and then
                    # the Django-provided example.com site was evaporating.
                    if uses_mysql(connection):
                        cursor.execute('SET FOREIGN_KEY_CHECKS=0')
                        for table in tables:
                            # Truncate implicitly commits.
                            cursor.execute('TRUNCATE `%s`' % table)
                        # TODO: necessary?
                        cursor.execute('SET FOREIGN_KEY_CHECKS=1')
                    else:
                        for table in tables:
                            cursor.execute('DELETE FROM %s' % table)

                transaction.commit(using=db)
                # cursor.close()  # Should be unnecessary, since we committed
                # any environment-setup statements that come with opening a new
                # cursor when we committed the fixtures.

    def _pre_setup(self):
        """Disable transaction methods, and clear some globals."""
        # Repeat stuff from TransactionTestCase, because I'm not calling its
        # _pre_setup, because that would load fixtures again.
        cache.cache.clear()
        settings.TEMPLATE_DEBUG = settings.DEBUG = False

        test.testcases.disable_transaction_methods()

        self.client = self.client_class()
        #self._fixture_setup()
        self._urlconf_setup()
        mail.outbox = []

        # Clear site cache in case somebody's mutated Site objects and then
        # cached the mutated stuff:
        from django.contrib.sites.models import Site
        Site.objects.clear_cache()

    def _post_teardown(self):
        """Re-enable transaction methods, and roll back any changes.

        Rollback clears any DB changes made by the test so the original fixture
        data is again visible.

        """
        # Rollback any mutations made by tests:
        test.testcases.restore_transaction_methods()
        for db in self._databases():
            transaction.rollback(using=db)

        self._urlconf_teardown()

        # We do not need to close the connection here to prevent
        # http://code.djangoproject.com/ticket/7572, since we commit, not
        # rollback, the test fixtures and thus any cursor startup statements.

        # Don't call through to superclass, because that would call
        # _fixture_teardown() and close the connection.

    @classmethod
    def _databases(cls):
        if getattr(cls, 'multi_db', False):
            return connections
        else:
            return [DEFAULT_DB_ALIAS]


class FastFixtureLiveServerTestCase(LiveServerTestCase):

    """
    Similar to django_nose.testcases.FastFixtureTestCase, except meant for Live Server tests.

    Test case that loads fixtures once and for all rather than once per test
    Using this can save huge swaths of time while still preserving test
    isolation. Fixture data is loaded at class setup time, and the transaction
    is committed. Commit and rollback methods are then monkeypatched away (like
    in Django's standard TestCase), and each test is run. After each test, the
    monkeypatching is temporarily undone, and a rollback is issued, returning
    the DB content to the pristine fixture state. Finally, upon class teardown,
    the DB is restored to a post-syncdb-like state by deleting the contents of
    any table that had been touched by a fixture (keeping infrastructure tables
    like django_content_type and auth_permission intact).

    Also includes the setupclass and teardownclass stuff from the Django LiveServerTestCase
    to start and stop a live server.

    Note that this is like Django's TestCase, not its TransactionTestCase, in
    that you cannot do your own commits or rollbacks from within tests.

    For best speed, group tests using the same fixtures into as few classes as
    possible. Better still, don't do that, and instead use the fixture-bundling
    plugin from django-nose, which does it dynamically at test time.
    """

    # from django_nose.testcases.FastFixtureTestCase
    cleans_up_after_itself = True  # This is the good kind of puppy.

    @classmethod
    def setUpClass(cls):
        """ a mix of django.test.testcases.LiveServerTestCase and django_nose.testcases.FastFixtureTestCase """

        # from django.test.testcases.LiveServerTestCase
        connections_override = {}
        for conn in connections.all():
            # If using in-memory sqlite databases, pass the connections to
            # the server thread.
            if (conn.settings_dict['ENGINE'].rsplit('.', 1)[-1] in ('sqlite3', 'spatialite')
                and conn.settings_dict['NAME'] == ':memory:'):
                # Explicitly enable thread-shareability for this connection
                conn.allow_thread_sharing = True
                connections_override[conn.alias] = conn

        # Launch the live server's thread
        specified_address = os.environ.get(
            'DJANGO_LIVE_TEST_SERVER_ADDRESS', 'localhost:8081')

        # The specified ports may be of the form '8000-8010,8080,9200-9300'
        # i.e. a comma-separated list of ports or ranges of ports, so we break
        # it down into a detailed list of all possible ports.
        possible_ports = []
        try:
            host, port_ranges = specified_address.split(':')
            for port_range in port_ranges.split(','):
                # A port range can be of either form: '8000' or '8000-8010'.
                extremes = list(map(int, port_range.split('-')))
                assert len(extremes) in [1, 2]
                if len(extremes) == 1:
                    # Port range of the form '8000'
                    possible_ports.append(extremes[0])
                else:
                    # Port range of the form '8000-8010'
                    for port in range(extremes[0], extremes[1] + 1):
                        possible_ports.append(port)
        except Exception:
            msg = 'Invalid address ("%s") for live server.' % specified_address
            six.reraise(ImproperlyConfigured, ImproperlyConfigured(msg), sys.exc_info()[2])
        cls.server_thread = test.testcases.LiveServerThread(
            host, possible_ports, connections_override)
        cls.server_thread.daemon = True
        cls.server_thread.start()

        # Wait for the live server to be ready
        cls.server_thread.is_ready.wait()
        if cls.server_thread.error:
            # Clean up behind ourselves, since tearDownClass won't get called in
            # case of errors.
            cls._tearDownClassInternal()
            raise cls.server_thread.error


        # from django_nose.testcases.FastFixtureTestCase
        # Turn on manual commits. Load and commit the fixtures.
        if not test.testcases.connections_support_transactions():
            raise NotImplementedError('%s supports only DBs with transaction '
                                      'capabilities.' % cls.__name__)
        for db in cls._databases():
            # These MUST be balanced with one leave_* each:
            transaction.enter_transaction_management(using=db)
            # Don't commit unless we say so:
            transaction.managed(True, using=db)

        cls._fixture_setup()

    @classmethod
    def _tearDownClassInternal(cls):
        """ from django.test.testcases.LiveServerTestCase """
        # There may not be a 'server_thread' attribute if setUpClass() for some
        # reasons has raised an exception.
        if hasattr(cls, 'server_thread'):
            # Terminate the live server's thread
            cls.server_thread.join()

        # Restore sqlite connections' non-sharability
        for conn in connections.all():
            if (conn.settings_dict['ENGINE'].rsplit('.', 1)[-1] in ('sqlite3', 'spatialite')
                and conn.settings_dict['NAME'] == ':memory:'):
                conn.allow_thread_sharing = False

    @classmethod
    def tearDownClass(cls):
        """ a mix of django.test.testcases.LiveServerTestCase and django_nose.testcases.FastFixtureTestCase """

        cls._tearDownClassInternal()    # from django.test.testcases.LiveServerTestCase

        # from django_nose.testcases.FastFixtureTestCase
        # Truncate the world, and turn manual commit management back off.
        cls._fixture_teardown()
        for db in cls._databases():
            # Finish off any transactions that may have happened in
            # tearDownClass in a child method.
            if transaction.is_dirty(using=db):
                transaction.commit(using=db)
            transaction.leave_transaction_management(using=db)

    @classmethod
    def _fixture_setup(cls):
        """
        From django_nose.testcases.FastFixtureTestCase, except for first time run fixture teardown fix
        Load fixture data, and commit.
        """
        for db in cls._databases():
            if (hasattr(cls, 'fixtures') and
                getattr(cls, '_fb_should_setup_fixtures', True)):
                # Iff the fixture-bundling test runner tells us we're the first
                # suite having these fixtures, set them up:
                cls._fixture_teardown() # dfeinzeig added to deal with case of first time run, clearing out any fixtures/data loaded via migrations
                call_command('loaddata', *cls.fixtures, **{'verbosity': 0,
                                                           'commit': False,
                                                           'database': db})
            # No matter what, to preserve the effect of cursor start-up
            # statements...
            transaction.commit(using=db)

    @classmethod
    def _fixture_teardown(cls):
        """
        From django_nose.testcases.FastFixtureTestCase
        Empty (only) the tables we loaded fixtures into, then commit.
        """
        if hasattr(cls, 'fixtures') and \
           getattr(cls, '_fb_should_teardown_fixtures', True):
            # If the fixture-bundling test runner advises us that the next test
            # suite is going to reuse these fixtures, don't tear them down.
            for db in cls._databases():
                tables = tables_used_by_fixtures(cls.fixtures, using=db)
                # TODO: Think about respecting _meta.db_tablespace, not just
                # db_table.
                if tables:
                    connection = connections[db]
                    cursor = connection.cursor()

                    # TODO: Rather than assuming that anything added to by a
                    # fixture can be emptied, remove only what the fixture
                    # added. This would probably solve input.mozilla.com's
                    # failures (since worked around) with Site objects; they
                    # were loading additional Sites with a fixture, and then
                    # the Django-provided example.com site was evaporating.
                    if uses_mysql(connection):
                        cursor.execute('SET FOREIGN_KEY_CHECKS=0')
                        for table in tables:
                            # Truncate implicitly commits.
                            cursor.execute('TRUNCATE `%s`' % table)
                        # TODO: necessary?
                        cursor.execute('SET FOREIGN_KEY_CHECKS=1')
                    else:
                        for table in tables:
                            cursor.execute('DELETE FROM %s' % table)

                transaction.commit(using=db)
                # cursor.close()  # Should be unnecessary, since we committed
                # any environment-setup statements that come with opening a new
                # cursor when we committed the fixtures.

    def _pre_setup(self):
        """
        From django_nose.testcases.FastFixtureTestCase
        Disable transaction methods, and clear some globals.
        """
        # Repeat stuff from TransactionTestCase, because I'm not calling its
        # _pre_setup, because that would load fixtures again.
        cache.cache.clear()
        settings.TEMPLATE_DEBUG = settings.DEBUG = False

        test.testcases.disable_transaction_methods()

        self.client = self.client_class()
        #self._fixture_setup()
        self._urlconf_setup()
        mail.outbox = []

        # Clear site cache in case somebody's mutated Site objects and then
        # cached the mutated stuff:
        from django.contrib.sites.models import Site
        Site.objects.clear_cache()

    def _post_teardown(self):
        """
        From django_nose.testcases.FastFixtureTestCase
        Re-enable transaction methods, and roll back any changes.
        Rollback clears any DB changes made by the test so the original fixture
        data is again visible.
        """
        # Rollback any mutations made by tests:
        test.testcases.restore_transaction_methods()
        for db in self._databases():
            transaction.rollback(using=db)

        self._urlconf_teardown()

        # We do not need to close the connection here to prevent
        # http://code.djangoproject.com/ticket/7572, since we commit, not
        # rollback, the test fixtures and thus any cursor startup statements.

        # Don't call through to superclass, because that would call
        # _fixture_teardown() and close the connection.

    @classmethod
    def _databases(cls):
        """ From django_nose.testcases.FastFixtureTestCase """
        if getattr(cls, 'multi_db', False):
            return connections
        else:
            return [DEFAULT_DB_ALIAS]
