============
Requirements
============

This package is most useful when installed with:

    * Django
    * nosetests

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
