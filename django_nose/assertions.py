# vim: tabstop=4 expandtab autoindent shiftwidth=4 fileencoding=utf-8

"""
Assertions that sort of follow Python unittest/Django test cases
"""

## Python

def fail_unless_equal(first, second, msg=None):
    assert first == second, (msg or '%s != %s' % (first, second))

assert_equal = assert_equals = fail_unless_equal

def fail_if_equal(first, second, msg=None):
    assert first != second, (msg or '%s == %s' % (first, second))

assert_not_equal = assert_not_equals = fail_if_equal

def fail_unless_almost_equal(first, second, places=7, msg=None):
    assert round(abs(second-first), places) != 0, (msg or '%s == %s within %s places' % (first, second, places))

assert_almost_equal = assert_almost_equals = fail_unless_almost_equal

def fail_if_almost_equal(first, second, places=7, msg=None):
    assert round(abs(second-first), places) == 0, (msg or '%s != %s within %s places' % (first, second, places))

assert_not_almost_equal = assert_not_almost_equals = fail_if_almost_equal

def fail_unless_raises(exc_class, callable_obj, *args, **kwargs):
    try:
        callable_obj(*args, **kwargs)
    except exc_class:
        return
    else:
        if hasattr(exc_class, '__name__'):
            exc_name = exc_class.__name__
        else:
            exc_name = str(exc_class)
        raise AssertionError('%s not raised' % exc_name)

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


