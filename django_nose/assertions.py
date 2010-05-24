# vim: tabstop=4 expandtab autoindent shiftwidth=4 fileencoding=utf-8

"""
Assertions that sort of follow Python unittest/Django test cases
"""

from django.test.testcases import to_list

from django.utils.encoding import smart_str

from django.http import QueryDict

from urlparse import urlsplit, urlunsplit

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
    if msg_prefix:
        msg_prefix = '%s: ' % msg_prefix

    assert response.status_code == status_code, msg_prefix + "Couldn't retrieve page: Response code was %d (expeced %d)" % (response.status_code, status_code)

    text = smart_str(text, response._charset)
    real_count = response.content.count(text)

    if count is not None:
        assert real_count == count, msg_prefix + "Found %d instances of '%s' in response (expected %d)" % (real_count, text, count)
    else:
        assert real_count != 0, msg_prefix + "Couldn't find '%s' in response" % text

def assert_not_contains(response, text, status_code=200, msg_prefix=''):
    if msg_prefix:
        msg_prefix = '%s: ' % msg_prefix

    assert response.status_code == status_code, msg_prefix + "Couldn't retrieve page: Response code was %d (expeced %d)" % (response.status_code, status_code)

    text = smart_str(text, response._charset)

    assert response.content.count(text) == 0, msg_prefix + "Response should not contain '%s'" % text

def assert_form_error(response, form, field, errors, msg_prefix=''):
    if msg_prefix:
        msg_prefix = '%s: ' % msg_prefix

    # Put context(s) into a list to simplify processing.
    contexts = to_list(response.context)

    assert contexts, msg_prefix + 'Response did not use any contexts to render the response'

    # Put error(s) into a list to simplify processing.
    errors = to_list(errors)

    found_form = False
    for i, context in enumerate(contexts):
        if form not in context:
            continue
        found_form = True
        for err in errors:
            if field:
                if field in context[form].errors:
                    field_errors = context[form].errors[field]
                    assert err in field_errors, msg_prefix + "The field '%s' on form '%s' in context %d does not contain the error '%s' (actual errors: %s)" % (field, form, i, err, repr(field_errors))
                elif field in context[form].fields:
                    raise AssertionError(msg_prefix + "The field '%s' on form '%s' in context %d contains no errors" % (field, form, i))
                else:
                    raise AssertionError(msg_prefix + "The form '%s' in context %d does not contain the field '%s'" % (form, i, field))

            else:
                non_field_errors = context[form].non_field_errors()
                assert err in non_field_errors, msg_prefix + "The form '%s' in context %d does not contain the non-field error '%s' (actual errors: %s)" % (form, i, err, non_field_errors)

    if not found_form:
        raise AssertionError(msg_prefix + "The form '%s' was not used to render the response" % form)

def assert_template_used(response, template_name, msg_prefix=''):
    if msg_prefix:
        msg_prefix = '%s: ' % msg_prefix

    template_names = [t.name for t in to_list(response.template)]
    if not template_names:
        raise AssertionError(msg_prefix + 'No templates used to render the response')

    assert template_name in template_names, msg_prefix + "Template '%s' was not a template used to render the response. Actual template(s) used: %s" % (template_name, u', '.join(template_names))

def assert_template_not_used(response, template_name, msg_prefix=''):
    if msg_prefix:
        msg_prefix = '%s: ' % msg_prefix

    template_names = [t.name for t in to_list(response.template)]
    assert template_name not in template_names, "Template '%s' was used unexpectedly in rendering the response" % template_name

def assert_redirects(response, expected_url, status_code=302, target_status_code=200, host=None, msg_prefix=''):
    if msg_prefix:
        msg_prefix = '%s: ' % msg_prefix

    if hasattr(response, 'redirect_chain'):
        # The request was a followed redirect
        assert len(response.redirect_chain), msg_prefix + "Response didn't redirect as expected: Response code was %d (expected %d)" % (response.status_code, status_code)

        assert response.redirect_chain[0][1] == status_code, msg_prefix + "Initial response didn't redirect as expected: Response code was %d (expected %d)" % (response.redirect_chain[0][1], status_Code)

        # 2010-05-24: mjt: is this a bug in Django?
        url, status_code = response.redirect_chain[-1]

        # 2010-05-24: mjt: Django says response.status_code == but we do not
        assert status_code == target_status_code, msg_prefix + "Response didn't redirect as expected: Final Response code was %d (expected %d)" % (status_code, target_status_code)

    else:
        # Not a followed redirect
        assert response.status_code == status_code, msg_prefix + "Response didn't redirect as expected: Response code was %d (expected %d)" % (response.status_code, status_code)

        url = response['Location']
        scheme, netloc, path, query, fragment = urlsplit(url)

        redirect_response = response.client.get(path, QueryDict(query))

        # Get the redirection page, using the same client that was used
        # to obtain the original response.
        assert redirect_response.status_code == target_status_code, msg_prefix + "Couldn't retrieve redirection page '%s': response code was %d (expected %d)" % (path, redirect_response.status_code, target_status_code)

    e_scheme, e_netloc, e_path, e_query, e_fragment = urlsplit(expected_url)
    if not (e_scheme or e_netloc):
        expected_url = urlunsplit(('http', host or 'testserver', e_path, e_query, e_fragment))

    assert url == expected_url, msg_prefix + "Response redirected to '%s, expected '%s'" % (url, expected_url)

# EOF


