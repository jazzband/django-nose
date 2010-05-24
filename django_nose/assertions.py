# vim: tabstop=4 expandtab autoindent shiftwidth=4 fileencoding=utf-8

"""
Assertions that sort of follow Python unittest/Django test cases
"""

## Python

def fail_unless_equal(first, second, msg=None):
    assert False

assert_equal = assert_equals = fail_unless_equal

def fail_if_equal(first, second, msg=None):
    assert False

assert_not_equal = assert_not_equals = fail_if_equal

def fail_unless_almost_equal(first, second, places=7, msg=None):
    assert False

assert_almost_equal = assert_almost_equals = fail_unless_almost_equal

def fail_if_almost_equal(first, second, places=7, msg=None):
    assert False

assert_not_almost_equal = assert_not_almost_equals = fail_if_almost_equal

def fail_unless_raises(exc_class, callable_obj, *args, **kwargs):
    assert False

assert_raises = fail_unless_raises

## Django

def assert_contains(response, text, count=None, status_code=200, msg_prefix=''):
    assert False

def assert_not_contains(response, text, status_code=200, msg_prefix=''):
    assert False

def assert_form_error(response, form, field, errors, msg_prefix=''):
    assert False

def assert_template_used(response, template_name, msg_prefix=''):
    assert False

def assert_redirects(response, expected_url, status_code=302, target_status_code=200, msg_prefix=''):
    assert False

# EOF


