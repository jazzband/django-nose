"""
Django test runner that invokes nose.

You can use

    NOSE_ARGS = ['list', 'of', 'args']

in settings.py for arguments that you always want passed to nose.
"""
import os
import sys

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection
from django.test import utils

import nose


def run_tests(test_labels, verbosity=1, interactive=True):
    """Test runner that invokes nose."""
    # Prepare django for testing.
    utils.setup_test_environment()
    old_db_name = settings.DATABASE_NAME
    connection.creation.create_test_db(verbosity, autoclobber=not interactive)

    # Pretend it's a production environment.
    settings.DEBUG = False

    # We pass nose a list of arguments that looks like sys.argv, but customize
    # to avoid unknown django arguments.
    nose_argv = ['nosetests']
    if hasattr(settings, 'NOSE_ARGS'):
        nose_argv.extend(settings.NOSE_ARGS)

    # Skip over 'manage.py test' and any arguments handled by django.
    django_opts = ['--noinput']
    for opt in BaseCommand.option_list:
        django_opts.extend(opt._long_opts)
        django_opts.extend(opt._short_opts)

    nose_argv.extend(opt for opt in sys.argv[2:] if
                     not any(opt.startswith(d) for d in django_opts))

    if verbosity >= 1:
        print ' '.join(nose_argv)

    try:
        success = nose.run(argv=nose_argv)
    finally:
        # Clean up django.
        connection.creation.destroy_test_db(old_db_name, verbosity)
        utils.teardown_test_environment()
        return success


def _get_options():
    """Return all nose options that don't conflict with django options."""
    cfg_files = nose.core.all_config_files()
    manager = nose.core.DefaultPluginManager()
    config = nose.core.Config(env=os.environ, files=cfg_files, plugins=manager)
    options = config.getParser().option_list
    django_opts = [opt.dest for opt in BaseCommand.option_list] + ['version']
    return tuple(o for o in options if o.dest not in django_opts and
                                       o.action != 'help')


run_tests.options = _get_options()
