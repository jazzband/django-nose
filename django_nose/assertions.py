# vim: tabstop=4 expandtab autoindent shiftwidth=4 fileencoding=utf-8

"""
Assertions that sort of follow Python unittest/Django test cases
"""

from django.test.testcases import TestCase

import re

## Python

from nose import tools
for t in dir(tools):
    if t.startswith('assert_'):
        vars()[t] = getattr(tools, t)

## Django

caps = re.compile('([A-Z])')

def pep8(name):
    return caps.sub(lambda m: '_' + m.groups()[0].lower(), name)


class Dummy(TestCase):
    def nop():
        pass
_t = Dummy('nop')

for at in [ at for at in dir(_t)
            if at.startswith('assert') and not '_' in at ]:
    pepd = pep8(at)
    vars()[pepd] = getattr(_t, at)

del Dummy
del _t
del pep8

## New

def assert_code(response, status_code, msg_prefix=''):
    if msg_prefix:
        msg_prefix = '%s: ' % msg_prefix

    assert response.status_code == status_code, \
        'Response code was %d (expected %d)' % \
            (response.status_code, status_code)

def assert_ok(response, msg_prefix=''):
    return assert_code(response, 200, msg_prefix=msg_prefix)

# EOF


