============
Requirements
============

This package is most useful when installed with:

    * Django 1.2+
    * nose


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

The use of django-nose is mostly transparent; just run ``./manage.py test`` as
usual. See ``./manage.py help test`` for all the options nose provides, and
look to the `nose docs`_ for more help with nose.

Fixture Bundling
----------------

django-nose includes a nose plugin which can drastically speed up your tests by
eliminating redundant setup of Django test fixtures. To activate the plugin,
add the ``--with-fixture-bundling`` option when running tests.

How Fixture Bundling Works
~~~~~~~~~~~~~~~~~~~~~~~~~~

The fixture bundler reorders your test classes so that ones with identical sets
of fixtures run adjacently. It then advises the first of each series to load
the fixtures once for all of them (and the remaining ones not to bother). It
also advises the last to tear them down. Depending on the size and repetition
of your fixtures, you can expect a 25% to 50% speed increase.

Incidentally, the author prefers to avoid Django fixtures, as they encourage
irrelevant coupling between tests and make tests harder to comprehend and
modify. For future tests, it is better to use the "model maker" pattern,
creating DB objects programmatically. This way, tests avoid setup they don't
need, and there is a clearer tie between a test and the exact state it
requires. The fixture bundler is intended to make existing tests, which have
already committed to fixtures, more tolerable.

Troubleshooting
~~~~~~~~~~~~~~~

If using ``--with-fixture-bundling`` causes test failures, it likely indicates
an order dependency between some of your tests. Here are the most frequent
sources of state leakage we have encountered:

* Locale activation, which is maintained in a threadlocal variable. Be sure to
  reset your locale selection between tests.
* memcached contents. Be sure to flush between tests.

Exempting A Class From Bundling
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In some unusual cases, it is desirable to exempt a test class from fixture
bundling, forcing it to set up and tear down its fixtures at the class
boundaries. For example, we might have a ``TestCase`` subclass which sets up
some state outside the DB in ``setUpClass`` and tears it down in
``tearDownClass``, and it might not be possible to adapt those routines to heed
the advice of the fixture bundler. In such a case, simply set the
``exempt_from_fixture_bundling`` attribute of the test class to ``True``.

Customization
-------------

Always Passing The Same Options
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To always set the same command line options you can use a `nose.cfg or
setup.cfg`_ (as usual) or you can specify them in settings.py like this::

    NOSE_ARGS = ['--failed', '--stop']

Using Custom Plugins
~~~~~~~~~~~~~~~~~~~~

If you need to `make custom plugins`_, you can define each plugin class
somewhere within your app and load them from settings.py like this::

    NOSE_PLUGINS = [
        'yourapp.tests.plugins.SystematicDysfunctioner',
        # ...
    ]

Just like middleware or anything else, each string must be a dot separated,
importable path to an actual class.  Each plugin class will be instantiated and
added to the Nose test runner.

Caveats
-------

`South`_ installs its own test command that turns off migrations during
testing.  Make sure that ``django_nose`` comes *after* ``south`` in
``INSTALLED_APPS`` so that django_nose's test command is used.

.. _nose docs: http://somethingaboutorange.com/mrl/projects/nose/
.. _nose.cfg or setup.cfg: http://somethingaboutorange.com/mrl/projects/nose/0.11.2/usage.html#configuration
.. _make custom plugins: http://somethingaboutorange.com/mrl/projects/nose/0.11.2/plugins.html#writing-plugins
.. _South: http://south.aeracode.org/


======================
Support for Django 1.1
======================

If you want to use django-nose with Django 1.1, use
https://github.com/jbalogh/django-nose/tree/django-1.1 or
http://pypi.python.org/pypi/django-nose/0.0.3.
