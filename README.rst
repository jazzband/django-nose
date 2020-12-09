===========
django-nose
===========

.. image:: https://img.shields.io/pypi/v/django-nose.svg
    :alt: The PyPI package
    :target: https://pypi.python.org/pypi/django-nose

.. image:: https://github.com/jazzband/django-nose/workflows/Test/badge.svg
    :target: https://github.com/jazzband/django-nose/actions
    :alt: GitHub Actions

.. image:: https://codecov.io/gh/jazzband/django-nose/branch/master/graph/badge.svg
    :alt: Coverage
    :target: https://codecov.io/gh/jazzband/django-nose

.. image:: https://jazzband.co/static/img/badge.svg
    :alt: Jazzband
    :target: https://jazzband.co/

.. Omit badges from docs

**django-nose** provides all the goodness of `nose`_ in your Django tests, like:

* Testing just your apps by default, not all the standard ones that happen to
  be in ``INSTALLED_APPS``
* Running the tests in one or more specific modules (or apps, or classes, or
  folders, or just running a specific test)
* Obviating the need to import all your tests into ``tests/__init__.py``.
  This not only saves busy-work but also eliminates the possibility of
  accidentally shadowing test classes.
* Taking advantage of all the useful `nose plugins`_

.. _nose: https://nose.readthedocs.io/en/latest/
.. _nose plugins: http://nose-plugins.jottit.com/

It also provides:

* Fixture bundling, an optional feature which speeds up your fixture-based
  tests by a factor of 4
* Reuse of previously created test DBs, cutting 10 seconds off startup time
* Hygienic TransactionTestCases, which can save you a DB flush per test
* Support for various databases. Tested with MySQL, PostgreSQL, and SQLite.
  Others should work as well.

django-nose requires nose 1.2.1 or later, and the `latest release`_ is
recommended.  It follows the `Django's support policy`_, supporting:

* Django 1.8 (LTS) with Python 3.5
* Django 1.9 with Python 3.5
* Django 1.10 with Python 3.5
* Django 1.11 (LTS) with Python 3.5 or 3.6
* Django 2.0 with Python 3.5, 3.6, or 3.7
* Django 2.1 with Python 3.5, 3.6, or 3.7
* Django 2.2 with Python 3.5, 3.6, or 3.7

.. _latest release: https://pypi.python.org/pypi/nose
.. _Django's support policy: https://docs.djangoproject.com/en/1.8/internals/release-process/#supported-versions


Note to users
-------------

`nose`_ has been in maintenance mode since at least 2015. ``django-nose`` is in
maintenance mode as well, and the sole maintainer is no longer an active user.
See `Jazzband.co`_ to learn how ``django-nose`` is maintained and how you can
help. New projects should consider using `pytest`_, or `unittest`_ with the
`Django testing framework`_.

.. _Jazzband.co: https://jazzband.co
.. _pytest: https://docs.pytest.org/en/stable/
.. _unittest: https://docs.python.org/3/library/unittest.html
.. _Django testing framework: https://docs.djangoproject.com/en/3.1/topics/testing/

Installation
------------

You can get django-nose from PyPI with... :

.. code-block:: shell

    $ pip install django-nose

The development version can be installed with... :

.. code-block:: shell

    $ pip install -e git://github.com/jazzband/django-nose.git#egg=django-nose

Since django-nose extends Django's built-in test command, you should add it to
your ``INSTALLED_APPS`` in ``settings.py``:

.. code-block:: python

    INSTALLED_APPS = (
        ...
        'django_nose',
        ...
    )

Then set ``TEST_RUNNER`` in ``settings.py``:

.. code-block:: python

    TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

Development
-----------
:Code:   https://github.com/jazzband/django-nose
:Issues: https://github.com/jazzband/django-nose/issues?state=open
:Docs:   https://django-nose.readthedocs.io
