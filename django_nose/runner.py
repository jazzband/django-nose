"""Django test runner that invokes nose.

You can use... ::

    NOSE_ARGS = ['list', 'of', 'args']

in settings.py for arguments that you want always passed to nose.

"""
import new
import os
import sys

from django.conf import settings
from django.core import exceptions
from django.core.management.base import BaseCommand
from django.core.management.color import no_style
from django.core.management.commands.loaddata import Command
from django.db import connections, transaction, DEFAULT_DB_ALIAS
from django.db.backends.creation import BaseDatabaseCreation
from django.db.models.loading import cache
from django.test.simple import DjangoTestSuiteRunner
from django.utils.importlib import import_module

import nose.core

from django_nose.plugin import DjangoSetUpPlugin, ResultPlugin, TestReorderer
from django_nose.utils import uses_mysql

try:
    any
except NameError:
    def any(iterable):
        for element in iterable:
            if element:
                return True
        return False


__all__ = ['BasicNoseRunner', 'NoseTestSuiteRunner']


# This is a table of Django's "manage.py test" options which
# correspond to nosetests options with a different name:
OPTION_TRANSLATION = {'--failfast': '-x'}


# Django v1.2 does not have a _get_test_db_name() function.
if not hasattr(BaseDatabaseCreation, '_get_test_db_name'):
    def _get_test_db_name(self):
        TEST_DATABASE_PREFIX = 'test_'

        if self.connection.settings_dict['TEST_NAME']:
            return self.connection.settings_dict['TEST_NAME']
        return TEST_DATABASE_PREFIX + self.connection.settings_dict['NAME']

    BaseDatabaseCreation._get_test_db_name = _get_test_db_name


def _get_plugins_from_settings():
    for plg_path in list(getattr(settings, 'NOSE_PLUGINS', [])) + ['django_nose.plugin.TestReorderer']:
        try:
            dot = plg_path.rindex('.')
        except ValueError:
            raise exceptions.ImproperlyConfigured(
                    "%s isn't a Nose plugin module" % plg_path)
        p_mod, p_classname = plg_path[:dot], plg_path[dot+1:]
        try:
            mod = import_module(p_mod)
        except ImportError, e:
            raise exceptions.ImproperlyConfigured(
                    'Error importing Nose plugin module %s: "%s"' % (p_mod, e))
        try:
            p_class = getattr(mod, p_classname)
        except AttributeError:
            raise exceptions.ImproperlyConfigured(
                    'Nose plugin module "%s" does not define a "%s"' %
                    (p_mod, p_classname))
        yield p_class()


def _get_options():
    """Return all nose options that don't conflict with django options."""
    cfg_files = nose.core.all_config_files()
    manager = nose.core.DefaultPluginManager()
    config = nose.core.Config(env=os.environ, files=cfg_files, plugins=manager)
    config.plugins.addPlugins(list(_get_plugins_from_settings()))
    options = config.getParser()._get_all_options()
    django_opts = [opt.dest for opt in BaseCommand.option_list] + ['version']
    return tuple(o for o in options if o.dest not in django_opts and
                                       o.action != 'help')


class BasicNoseRunner(DjangoTestSuiteRunner):
    """Facade that implements a nose runner in the guise of a Django runner

    You shouldn't have to use this directly unless the additions made by
    ``NoseTestSuiteRunner`` really bother you. They shouldn't, because they're
    all off by default.

    """
    __test__ = False

    # Replace the builtin command options with the merged django/nose options:
    options = _get_options()

    def run_suite(self, nose_argv):
        result_plugin = ResultPlugin()
        plugins_to_add = [DjangoSetUpPlugin(self),
                          result_plugin,
                          TestReorderer()]

        for plugin in _get_plugins_from_settings():
            plugins_to_add.append(plugin)

        nose.core.TestProgram(argv=nose_argv, exit=False,
                              addplugins=plugins_to_add)
        return result_plugin.result

    def run_tests(self, test_labels, extra_tests=None):
        """Run the unit tests for all the test names in the provided list.

        Test names specified may be file or module names, and may optionally
        indicate the test case to run by separating the module or file name
        from the test case name with a colon. Filenames may be relative or
        absolute. Examples:

        runner.run_tests('test.module')
        runner.run_tests('another.test:TestCase.test_method')
        runner.run_tests('a.test:TestCase')
        runner.run_tests('/path/to/test/file.py:test_function')

        Returns the number of tests that failed.

        """
        nose_argv = (['nosetests', '--verbosity', str(self.verbosity)]
                     + list(test_labels))
        if hasattr(settings, 'NOSE_ARGS'):
            nose_argv.extend(settings.NOSE_ARGS)

        # Skip over 'manage.py test' and any arguments handled by django.
        django_opts = ['--noinput', '--liveserver']
        for opt in BaseCommand.option_list:
            django_opts.extend(opt._long_opts)
            django_opts.extend(opt._short_opts)

        nose_argv.extend(
            OPTION_TRANSLATION.get(opt, opt) for opt in sys.argv[1:]
            if opt.startswith('-')
               and not any(opt.startswith(d) for d in django_opts))

        if self.verbosity >= 1:
            print ' '.join(nose_argv)

        result = self.run_suite(nose_argv)
        # suite_result expects the suite as the first argument.  Fake it.
        return self.suite_result({}, result)


_old_handle = Command.handle
def _foreign_key_ignoring_handle(self, *fixture_labels, **options):
    """Wrap the the stock loaddata to ignore foreign key checks so we can load circular references from fixtures.

    This is monkeypatched into place in setup_databases().

    """
    using = options.get('database', DEFAULT_DB_ALIAS)
    commit = options.get('commit', True)
    connection = connections[using]

    # MySQL stinks at loading circular references:
    if uses_mysql(connection):
        cursor = connection.cursor()
        cursor.execute('SET foreign_key_checks = 0')

    _old_handle(self, *fixture_labels, **options)

    if uses_mysql(connection):
        cursor = connection.cursor()
        cursor.execute('SET foreign_key_checks = 1')

        if commit:
            connection.close()


def _skip_create_test_db(self, verbosity=1, autoclobber=False):
    """Database creation class that skips both creation and flushing

    The idea is to re-use the perfectly good test DB already created by an
    earlier test run, cutting the time spent before any tests run from 5-13
    (depending on your I/O luck) down to 3.

    """
    # Notice that the DB supports transactions. Originally, this was done in
    # the method this overrides. Django v1.2 does not have the confirm
    # function. Added in https://code.djangoproject.com/ticket/12991.
    if hasattr(self.connection.features, 'confirm') and \
       callable(self.connection.features.confirm):
        self.connection.features.confirm()
    else:
        can_rollback = self._rollback_works()
        self.connection.settings_dict["SUPPORTS_TRANSACTIONS"] = can_rollback

    return self._get_test_db_name()


def _reusing_db():
    """Return whether the ``REUSE_DB`` flag was passed"""
    return os.getenv('REUSE_DB', 'false').lower() in ('true', '1', '')


def _can_support_reuse_db(connection):
    """Return whether it makes any sense to use REUSE_DB with the backend of a connection."""
    # This is a SQLite in-memory DB. Those are created implicitly when
    # you try to connect to them, so our test below doesn't work.
    return not connection.creation._get_test_db_name() == ':memory:'


def _should_create_database(connection):
    """Return whether we should recreate the given DB.

    This is true if the DB doesn't exist or the REUSE_DB env var isn't truthy.

    """
    # TODO: Notice when the Model classes change and return True. Worst case,
    # we can generate sqlall and hash it, though it's a bit slow (2 secs) and
    # hits the DB for no good reason. Until we find a faster way, I'm inclined
    # to keep making people explicitly saying REUSE_DB if they want to reuse
    # the DB.

    if not _can_support_reuse_db(connection):
        return True

    # Notice whether the DB exists, and create it if it doesn't:
    try:
        connection.cursor()
    except StandardError:  # TODO: Be more discerning but still DB agnostic.
        return True
    return not _reusing_db()


def _mysql_reset_sequences(style, connection):
    """Return a list of SQL statements needed to reset all sequences for Django tables."""
    tables = connection.introspection.django_table_names(only_existing=True)
    flush_statements = connection.ops.sql_flush(
            style, tables, connection.introspection.sequence_list())

    # connection.ops.sequence_reset_sql() is not implemented for MySQL,
    # and the base class just returns []. TODO: Implement it by pulling
    # the relevant bits out of sql_flush().
    return [s for s in flush_statements if s.startswith('ALTER')]
    # Being overzealous and resetting the sequences on non-empty tables
    # like django_content_type seems to be fine in MySQL: adding a row
    # afterward does find the correct sequence number rather than
    # crashing into an existing row.


class NoseTestSuiteRunner(BasicNoseRunner):
    """A runner that optionally skips DB creation

    This test monkeypatches connection.creation to let you skip creating
    databases if they already exist. Your tests will run much faster.

    To opt into this behavior, set the environment variable ``REUSE_DB`` to
    something that isn't "0" or "false" (case aside).

    """
    def setup_databases(self):
        for alias in connections:
            connection = connections[alias]
            creation = connection.creation
            test_db_name = creation._get_test_db_name()

            # Mess with the DB name so other things operate on a test DB
            # rather than the real one. This is done in create_test_db when
            # we don't monkeypatch it away with _skip_create_test_db.
            orig_db_name = connection.settings_dict['NAME']
            connection.settings_dict['NAME'] = test_db_name

            if not _reusing_db() and _can_support_reuse_db(connection):
                print ('To reuse old database "%s" for speed, set env var '
                       'REUSE_DB=1.' % test_db_name)

            if _should_create_database(connection):
                # We're not using _skip_create_test_db, so put the DB name back:
                connection.settings_dict['NAME'] = orig_db_name

                # Since we replaced the connection with the test DB, closing
                # the connection will avoid pooling issues with SQLAlchemy. The
                # issue is trying to CREATE/DROP the test database using a
                # connection to a DB that was established with that test DB.
                # MySQLdb doesn't allow it, and SQLAlchemy attempts to reuse
                # the existing connection from its pool.
                connection.close()
            else:
                # Reset auto-increment sequences. Apparently, SUMO's tests are
                # horrid and coupled to certain numbers.
                cursor = connection.cursor()
                style = no_style()

                if uses_mysql(connection):
                    reset_statements = _mysql_reset_sequences(style, connection)
                else:
                    reset_statements = connection.ops.sequence_reset_sql(
                            style, cache.get_models())

                for reset_statement in reset_statements:
                    cursor.execute(reset_statement)

                # Django v1.3 (https://code.djangoproject.com/ticket/9964)
                # starts using commit_unless_managed() for individual
                # connections. Backwards compatibility for Django 1.2 is to use
                # the generic transaction function.
                transaction.commit_unless_managed(using=connection.alias)

                creation.create_test_db = new.instancemethod(
                        _skip_create_test_db, creation, creation.__class__)

        Command.handle = _foreign_key_ignoring_handle

        # With our class patch, does nothing but return some connection
        # objects:
        return super(NoseTestSuiteRunner, self).setup_databases()

    def teardown_databases(self, *args, **kwargs):
        """Leave those poor, reusable databases alone if REUSE_DB is true."""
        if not _reusing_db():
            return super(NoseTestSuiteRunner, self).teardown_databases(
                    *args, **kwargs)
        # else skip tearing down the DB so we can reuse it next time
