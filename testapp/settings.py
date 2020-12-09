"""
Django settings for testing django-nose.

Configuration is overriden by environment variables:

DATABASE_URL - See https://github.com/joke2k/django-environ
USE_SOUTH - Set to 1 to include South in INSTALLED_APPS
TEST_RUNNER - Dotted path of test runner to use (can also use --test-runner)
NOSE_PLUGINS - Comma-separated list of plugins to add
"""
from os import path
import environ

env = environ.Env(
    # set casting, default value
    DEBUG=(bool, False)
)

BASE_DIR = path.dirname(path.dirname(__file__))

DATABASES = {"default": env.db("DATABASE_URL", default="sqlite:////tmp/test.sqlite")}

MIDDLEWARE_CLASSES = ()

INSTALLED_APPS = [
    "django_nose",
    "testapp",
]

TEST_RUNNER = env("TEST_RUNNER", default="django_nose.NoseTestSuiteRunner")

NOSE_PLUGINS = env.list("NOSE_PLUGINS", default=[])

SECRET_KEY = "ssshhhh"
