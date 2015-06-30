"""The Basic configuration, plus a plugin."""
from .settings import *  # nopep8


NOSE_PLUGINS = [
    'testapp.plugins.SanityCheckPlugin'
]
