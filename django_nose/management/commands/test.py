from optparse import make_option
import sys

from django.conf import settings
from django.core import management
from django.core.management.base import BaseCommand
from django.test.utils import get_runner


TestRunner = get_runner(settings)

if hasattr(TestRunner, 'options'):
    extra_options = TestRunner.options
else:
    extra_options = []


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--noinput', action='store_false', dest='interactive', default=True,
            help='Tells Django to NOT prompt the user for input of any kind.'),
        make_option('--failfast', action='store_true', dest='failfast', default=False,
            help='Tells Django to stop running the test suite after first failed test.'),
    ) + tuple(extra_options)
    help = 'Runs the test suite for the specified applications, or the entire site if no apps are specified.'
    args = '[appname ...]'

    requires_model_validation = False

    def handle(self, *test_labels, **options):

        verbosity = int(options.get('verbosity', 1))
        interactive = options.get('interactive', True)
        failfast = options.get('failfast', False)

        if management._commands['syncdb'] == 'south':
            # South has its own test command that turns off migrations
            # during testings.  If we detected south, we need to fix syncdb.
            management._commands['syncdb'] = 'django.core'

        if hasattr(TestRunner, 'func_name'):
            # Pre 1.2 test runners were just functions,
            # and did not support the 'failfast' option.
            import warnings
            warnings.warn(
                'Function-based test runners are deprecated. Test runners should be classes with a run_tests() method.',
                PendingDeprecationWarning
            )
            failures = TestRunner(test_labels, verbosity=verbosity, interactive=interactive)
        else:
            test_runner = TestRunner(verbosity=verbosity, interactive=interactive, failfast=failfast)
            failures = test_runner.run_tests(test_labels)

        if failures:
            sys.exit(failures)
