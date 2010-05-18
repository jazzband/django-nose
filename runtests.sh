#!/bin/sh

export PYTHONPATH=.

django_test() {
    TEST="django-admin.py test --settings=testapp.$1"
    $TEST 2>&1 | grep 'Ran 1 test' > /dev/null
    if [ $? -gt 0 ]
    then
        echo FAIL: $2
        $TEST
        exit 1;
    else
        echo PASS: $2
    fi

    # Check that we're hijacking the help correctly.
    $TEST --help 2>&1 | grep 'NOSE_DETAILED_ERRORS' > /dev/null
    if [ $? -gt 0 ]
    then
        echo FAIL: $2 '(--help)'
        exit 1;
    else
        echo PASS: $2 '(--help)'
    fi
}

django_test 'settings' 'normal settings'
django_test 'settings_with_south' 'with south in installed apps'
django_test 'settings_old_style' 'django_nose.run_tests format'
