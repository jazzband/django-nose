"""Django with south for database migrations."""
from .settings import *  # nopep8


INSTALLED_APPS = ('south',) + INSTALLED_APPS
