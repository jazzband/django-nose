from optparse import make_option
import sys

from django.conf import settings
from django.core import management
from django.core.management.commands.test import Command
from django.test.utils import get_runner


try:
    """I wish south worked with Django trunk."""
    # from south.management.commands.test import Command
except ImportError:
    pass


TestRunner = get_runner(settings)

if hasattr(TestRunner, 'options'):
    extra_options = TestRunner.options
else:
    extra_options = []


class Command(Command):
    option_list = Command.option_list + tuple(extra_options)
