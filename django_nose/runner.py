"""Django test runner that invokes nose.

You can use... ::

    NOSE_ARGS = ['list', 'of', 'args']

in settings.py for arguments that you want always passed to nose.

"""
import os
import sys

from django.conf import settings
from django.core import exceptions
from django.core.management.base import BaseCommand
from django.core.management.color import no_style
from django.core.management.commands.loaddata import Command
from django.db import connections, DEFAULT_DB_ALIAS
from django.db.backends.mysql import creation as mysql
from django.test.simple import DjangoTestSuiteRunner
from django.utils.importlib import import_module

import nose.core

from django_nose.plugin import DjangoSetUpPlugin, ResultPlugin

try:
    any
except NameError:
    def any(iterable):
        for element in iterable:
            if element:
                return True
        return False


__all__ = ['BasicNoseRunner', 'NoseTestSuiteRunner', 'uses_mysql']


# This is a table of Django's "manage.py test" options which
# correspond to nosetests options with a different name:
OPTION_TRANSLATION = {'--failfast': '-x'}


def uses_mysql(connection):
    return 'mysql' in connection.settings_dict['ENGINE']


def _get_plugins_from_settings():
    for plg_path in list(getattr(settings, 'NOSE_PLUGINS', [])) + ['django_nose.fixture_bundling.FixtureBundlingPlugin']:
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
    ``NoseTestSuiteRunner`` really bother you.

    """
    __test__ = False

    # Replace the builtin command options with the merged django/nose options:
    options = _get_options()

    def run_suite(self, nose_argv):
        result_plugin = ResultPlugin()
        plugins_to_add = [DjangoSetUpPlugin(self), result_plugin]

        for plugin in _get_plugins_from_settings():
            plugins_to_add.append(plugin)

        nose.core.TestProgram(argv=nose_argv, exit=False,
                              addplugins=plugins_to_add)
        return result_plugin.result

    def run_tests(self, test_labels, extra_tests=None):
        """
        Run the unit tests for all the test names in the provided list.

        Test names specified may be file or module names, and may optionally
        indicate the test case to run by separating the module or file name
        from the test case name with a colon. Filenames may be relative or
        absolute.  Examples:

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
        django_opts = ['--noinput']
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
    """Wrap the the stock loaddata to ignore foreign key checks so we can load
    circular references from fixtures.

    This is monkeypatched into place in setup_databases().

    """
    using = options.get('database', DEFAULT_DB_ALIAS)
    commit = options.get('commit', True)
    connection = connections[using]

    if uses_mysql(connection):
        cursor = connection.cursor()
        cursor.execute('SET foreign_key_checks = 0')

    _old_handle(self, *fixture_labels, **options)

    if uses_mysql(connection):
        cursor = connection.cursor()
        cursor.execute('SET foreign_key_checks = 1')

        if commit:
            connection.close()


class SkipDatabaseCreation(mysql.DatabaseCreation):
    """Database creation class that skips both creation and flushing

    The idea is to re-use the perfectly good test DB already created by an
    earlier test run, cutting the time spent before any tests run from 5-13
    (depending on your I/O luck) down to 3.

    """
    def create_test_db(self, verbosity=1, autoclobber=False):
        # Notice that the DB supports transactions. Originally, this was done
        # in the method this overrides.
        self.connection.features.confirm()
        return self._get_test_db_name()


class NoseTestSuiteRunner(BasicNoseRunner):
    """A runner that skips DB creation when possible

    This test monkeypatches connection.creation to let you skip creating
    databases if they already exist. Your tests will run much faster.

    To opt into this behavior, set the environment variable ``REUSE_DB`` to
    something that isn't "0" or "false" (case aside).

    """
    def setup_databases(self):
        def should_create_database(connection):
            """Return whether we should recreate the given DB.

            This is true if the DB doesn't exist or the REUSE_DB env var
            isn't truthy.

            """
            # TODO: Notice when the Model classes change and return True. Worst
            # case, we can generate sqlall and hash it, though it's a bit slow
            # (2 secs) and hits the DB for no good reason. Until we find a
            # faster way, I'm inclined to keep making people explicitly saying
            # REUSE_DB if they want to reuse the DB.

            # Notice whether the DB exists, and create it if it doesn't:
            try:
                connection.cursor()
            except StandardError:  # TODO: Be more discerning but still DB
                                   # agnostic.
                return True
            return not (os.getenv('REUSE_DB', 'false').lower() in
                        ('true', '1', ''))

        def sql_reset_sequences(connection):
            """Return a list of SQL statements needed to reset all sequences
            for Django tables."""
            # TODO: This is MySQL-specific--see below. It should also work with
            # SQLite but not Postgres. :-(
            tables = connection.introspection.django_table_names(
                only_existing=True)
            flush_statements = connection.ops.sql_flush(
                no_style(), tables, connection.introspection.sequence_list())

            # connection.ops.sequence_reset_sql() is not implemented for MySQL,
            # and the base class just returns []. TODO: Implement it by pulling
            # the relevant bits out of sql_flush().
            return [s for s in flush_statements if s.startswith('ALTER')]
            # Being overzealous and resetting the sequences on non-empty tables
            # like django_content_type seems to be fine in MySQL: adding a row
            # afterward does find the correct sequence number rather than
            # crashing into an existing row.

        for alias in connections:
            connection = connections[alias]
            creation = connection.creation
            test_db_name = creation._get_test_db_name()

            # Mess with the DB name so other things operate on a test DB
            # rather than the real one. This is done in create_test_db when
            # we don't monkeypatch it away with SkipDatabaseCreation.
            orig_db_name = connection.settings_dict['NAME']
            connection.settings_dict['NAME'] = test_db_name

            if not should_create_database(connection):
                # Reset auto-increment sequences. Apparently, SUMO's tests are
                # horrid and coupled to certain numbers.
                cursor = connection.cursor()
                for statement in sql_reset_sequences(connection):
                    cursor.execute(statement)
                connection.commit_unless_managed()  # which it is

                creation.__class__ = SkipDatabaseCreation
            else:
                print ('To reuse old database "%s" for speed, set env var '
                       'REUSE_DB=1' % test_db_name)
                # We're not using SkipDatabaseCreation, so put the DB name
                # back.
                connection.settings_dict['NAME'] = orig_db_name

        Command.handle = _foreign_key_ignoring_handle

        # With our class patch, does nothing but return some connection
        # objects:
        return super(NoseTestSuiteRunner, self).setup_databases()

    def teardown_databases(self, old_config, **kwargs):
        """Leave those poor, reusable databases alone."""
