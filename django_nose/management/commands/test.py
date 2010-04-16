from optparse import make_option
import sys

from django.conf import settings
from django.core import management
from django.core.management.base import BaseCommand
from django.test.utils import get_runner


test_runner = get_runner(settings)

if hasattr(test_runner, 'options'):
    extra_options = test_runner.options
else:
    extra_options = []


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--noinput', action='store_false', dest='interactive', default=True,
            help='Tells Django to NOT prompt the user for input of any kind.'),
    ) + tuple(extra_options)
    help = 'Runs the test suite for the specified applications, or the entire site if no apps are specified.'
    args = '[appname ...]'

    requires_model_validation = False

    def handle(self, *test_labels, **options):

        verbosity = int(options.get('verbosity', 1))
        interactive = options.get('interactive', True)

        if 'south' in settings.INSTALLED_APPS:
            if hasattr(settings, "SOUTH_TESTS_MIGRATE") and not settings.SOUTH_TESTS_MIGRATE:
                # point at the core syncdb command when creating tests
                # tests should always be up to date with the most recent model structure
                management._commands['syncdb'] = 'django.core'
            else:
                from south.management.commands.test import MigrateAndSyncCommand
                management._commands['syncdb'] = MigrateAndSyncCommand()

        failures = test_runner(test_labels, verbosity=verbosity, interactive=interactive)
        if failures:
            sys.exit(failures)
