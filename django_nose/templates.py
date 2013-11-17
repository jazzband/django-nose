"""
Generate tests for compiling each Django template to validate them.
"""

import os
import re
import unittest

from nose.plugins import base


def is_descendant(ancestor, descendant):
    return os.path.join(descendant, '').startswith(os.path.join(ancestor, ''))


class DjangoTemplates(base.Plugin):
    __doc__

    name = 'django-templates'
    test_name_pattern = re.compile(r'\W')

    def configure(self, options, config):
        """Make sure the Django template loader cache is populated."""
        base.Plugin.configure(self, options, config)
        from django.template import loader
        try:
            loader.find_template('')
        except loader.TemplateDoesNotExist:
            pass

        self.sources = set()
        self.loader = unittest.TestLoader()

    def wantDirectory(self, path):
        """Select all files in a Django templates directory if enabled."""
        from django.template import loader
        for source in self.sources:
            if is_descendant(source, path):
                return None
        for source_loader in loader.template_source_loaders:
            try:
                sources = source_loader.get_template_sources('.')
            except loader.TemplateDoesNotExist:
                continue
            for source in sources:
                if is_descendant(source, path):
                    self.sources.add(source)
                    return True
        return None

    def loadTestsFromDir(self, path):
        """Construct tests for all files in a Django templates directory."""
        if path not in self.sources:
            return None

        from django.template import loader
        from django import test

        tests = {}
        for root, dirs, files in os.walk(path):
            for filename in files:
                file_path = os.path.join(root, filename)
                if not os.path.isfile(file_path):
                    # self.wantDirectory will handle directories
                    continue

                def generatedDjangoTemplateTest(test, file_path=file_path):
                    template = loader.get_template(file_path[len(path) + 1:])
                    test.assertTrue(
                        callable(getattr(template, 'render', None)))

                generatedDjangoTemplateTest.__doc__ = (
                    "Template compiles: {0!r}".format(
                        os.path.relpath(file_path)))
                test_name = 'test_django_template_{0}'.format(
                    self.test_name_pattern.sub('_', filename))
                generatedDjangoTemplateTest.func_name = test_name
                tests[test_name] = generatedDjangoTemplateTest

        case = type('DjangoTemplateTestCase', (test.TestCase, ), tests)
        return self.loader.loadTestsFromTestCase(case)
