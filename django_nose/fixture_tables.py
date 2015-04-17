"""A copy of Django 1.7.7's stock loaddata.py, adapted so that, instead of
loading any data, it returns the tables referenced by a set of fixtures so we
can truncate them (and no others) quickly after we're finished with them."""

from __future__ import unicode_literals

import glob
import gzip
import os
import six
import warnings
import zipfile
from optparse import make_option

from django.apps import apps
from django.conf import settings
from django.core import serializers
from django.core.management.base import BaseCommand, CommandError
from django.core.management.color import no_style
from django.db import (connections, router, transaction, DEFAULT_DB_ALIAS,
      IntegrityError, DatabaseError)
from django.utils import lru_cache
from django.utils.encoding import force_text
from django.utils.functional import cached_property
from django.utils._os import upath
from django.utils.deprecation import RemovedInDjango19Warning
from itertools import product

try:
    import bz2
    has_bz2 = True
except ImportError:
    has_bz2 = False


def tables_used_by_fixtures(fixture_labels, using=DEFAULT_DB_ALIAS):

    connection = connections[using]

    # Keep a count of the installed objects and fixtures
    fixture_count = 0
    models = set()

    if has_bz2:
        compression_formats['bz2'] = (bz2.BZ2File, 'r')

    with connection.constraint_checks_disabled():
        for fixture_label in fixture_labels:
            models.update(get_models(fixture_label, using))

    # Since we disabled constraint checks, we must manually check for
    # any invalid keys that might have been added
    table_names = {model._meta.db_table for model in models}
    return table_names


def get_models(fixture_label, using):
    """
    Loads fixtures files for a given label.
    """
    models = set()
    for fixture_file, fixture_dir, fixture_name in find_fixtures(fixture_label, using):
        _, ser_fmt, cmp_fmt = parse_name(os.path.basename(fixture_file))
        open_method, mode = compression_formats[cmp_fmt]
        fixture = open_method(fixture_file, mode)
        try:
            objects_in_fixture = 0
            loaded_objects_in_fixture = 0

            objects = serializers.deserialize(ser_fmt, fixture,
                using=using)  # ignorenonexistent=self.ignore

            for obj in objects:
                objects_in_fixture += 1
                models.add(obj.object.__class__)

        except Exception as e:
            raise Exception("Problem installing fixture '%s': %s" % (fixture_file, e),)
        finally:
            fixture.close()

        # Warn if the fixture we loaded contains 0 objects.
        if objects_in_fixture == 0:
            warnings.warn(
                "No fixture data found for '%s'. (File format may be "
                "invalid.)" % fixture_name,
                RuntimeWarning
            )

    return models

@lru_cache.lru_cache(maxsize=None)
def find_fixtures(fixture_label, using):
    """
    Finds fixture files for a given label.
    """
    fixture_name, ser_fmt, cmp_fmt = parse_name(fixture_label)
    databases = [using, None]
    cmp_fmts = list(compression_formats.keys()) if cmp_fmt is None else [cmp_fmt]
    ser_fmts = serializers.get_public_serializer_formats() if ser_fmt is None else [ser_fmt]

    if os.path.isabs(fixture_name):
        directories = [os.path.dirname(fixture_name)]
        fixture_name = os.path.basename(fixture_name)
    else:
        directories = fixture_dirs()
        if os.path.sep in fixture_name:
            directories = [os.path.join(dir_, os.path.dirname(fixture_name))
                            for dir_ in directories]
            fixture_name = os.path.basename(fixture_name)

    suffixes = ('.'.join(ext for ext in combo if ext)
            for combo in product(databases, ser_fmts, cmp_fmts))
    targets = set('.'.join((fixture_name, suffix)) for suffix in suffixes)

    fixture_files = []
    for fixture_dir in directories:
        fixture_files_in_dir = []
        for candidate in glob.iglob(os.path.join(fixture_dir, fixture_name + '*')):
            if os.path.basename(candidate) in targets:
                # Save the fixture_dir and fixture_name for future error messages.
                fixture_files_in_dir.append((candidate, fixture_dir, fixture_name))

        # Check kept for backwards-compatibility; it isn't clear why
        # duplicates are only allowed in different directories.
        if len(fixture_files_in_dir) > 1:
            raise CommandError(
                "Multiple fixtures named '%s' in %s. Aborting." %
                (fixture_name, humanize(fixture_dir)))
        fixture_files.extend(fixture_files_in_dir)

    if fixture_name != 'initial_data' and not fixture_files:
        # Warning kept for backwards-compatibility; why not an exception?
        warnings.warn("No fixture named '%s' found." % fixture_name)
    elif fixture_name == 'initial_data' and fixture_files:
        warnings.warn(
            'initial_data fixtures are deprecated. Use data migrations instead.',
            RemovedInDjango19Warning
        )

    return fixture_files

@lru_cache.lru_cache(maxsize=None)
def fixture_dirs():
    """
    Return a list of fixture directories.

    The list contains the 'fixtures' subdirectory of each installed
    application, if it exists, the directories in FIXTURE_DIRS, and the
    current directory.
    """
    dirs = []
    for app_config in apps.get_app_configs():
        app_dir = os.path.join(app_config.path, 'fixtures')
        if os.path.isdir(app_dir):
            dirs.append(app_dir)
    dirs.extend(list(settings.FIXTURE_DIRS))
    dirs.append('')
    dirs = [upath(os.path.abspath(os.path.realpath(d))) for d in dirs]
    return dirs

def parse_name(fixture_name):
    """
    Splits fixture name in name, serialization format, compression format.
    """
    parts = fixture_name.rsplit('.', 2)

    if len(parts) > 1 and parts[-1] in compression_formats:
        cmp_fmt = parts[-1]
        parts = parts[:-1]
    else:
        cmp_fmt = None

    if len(parts) > 1:
        if parts[-1] in serialization_formats:
            ser_fmt = parts[-1]
            parts = parts[:-1]
        else:
            raise CommandError(
                "Problem installing fixture '%s': %s is not a known "
                "serialization format." % (''.join(parts[:-1]), parts[-1]))
    else:
        ser_fmt = None

    name = '.'.join(parts)

    return name, ser_fmt, cmp_fmt


class SingleZipReader(zipfile.ZipFile):

    def __init__(self, *args, **kwargs):
        zipfile.ZipFile.__init__(self, *args, **kwargs)
        if len(self.namelist()) != 1:
            raise ValueError("Zip-compressed fixtures must contain one file.")

    def read(self):
        return zipfile.ZipFile.read(self, self.namelist()[0])


def humanize(dirname):
    return "'%s'" % dirname if dirname else 'absolute path'


# Forcing binary mode may be revisited after dropping Python 2 support (see #22399)
compression_formats = {
    None: (open, 'rb'),
    'gz': (gzip.GzipFile, 'rb'),
    'zip': (SingleZipReader, 'r'),
}

serialization_formats = serializers.get_public_serializer_formats()
