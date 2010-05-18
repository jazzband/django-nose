============
Requirements
============

This package is most useful when installed with:

    * Django
    * nosetests


===========================
Upgrading from Django < 1.2
===========================

Django 1.2 switches to a `class-based test runner`_.  To use ``django-nose``
with Django 1.2, change your ``TEST_RUNNER`` from ``django_nose.run_tests`` to
``django_nose.NoseTestSuiteRunner``.

``django_nose.run_tests`` will continue to work in Django 1.2, but will raise a
warning.  In Django 1.3 it will stop working.

If you were using ``django_nose.run_gis_tests``, you should also switch to
``django_nose.NoseTestSuiteRunner`` and use one of the `spatial backends`_ in
your ``DATABASES`` settings.

.. _class-based test runner: http://docs.djangoproject.com/en/dev/releases/1.2/#function-based-test-runners
.. _spatial backends: http://docs.djangoproject.com/en/dev/ref/contrib/gis/db-api/#id1


Installation
------------

You can get django-nose from pypi with: ::

    pip install django-nose

The development version can be installed with: ::

    pip install -e git://github.com/jbalogh/django-nose.git#egg=django-nose

Since django-nose extends Django's built-in test command, you should add it to
your ``INSTALLED_APPS`` in ``settings.py``: ::

    INSTALLED_APPS = (
        ...
        'django_nose',
        ...
    )

Then set ``TEST_RUNNER`` in ``settings.py``: ::

    TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'


Usage
-----

See ``django help test`` for all the options nose provides, and look to the `nose
docs`_ for more help with nose.

Caveats
-------

`South`_ installs its own test command that turns off migrations during
testing.  Make sure that ``django_nose`` comes *after* ``south`` in
``INSTALLED_APPS`` so that django_nose's test command is used.

.. _nose docs: http://somethingaboutorange.com/mrl/projects/nose/
.. _South: http://south.aeracode.org/
