#!/bin/bash

export PYTHONPATH=.

PYTHONVERSION=$(python --version 2>&1)
PYTHONVERSION=${PYTHONVERSION##Python }

function version { echo $@ | gawk -F. '{ printf("%d.%d.%d\n", $1,$2,$3); }'; }

reset_env() {
    export USE_SOUTH=
    export TEST_RUNNER=
    export NOSE_PLUGINS=
    export REUSE_DB=
}

django_test() {
    COMMAND=$1
    TEST_COUNT=$2
    DESCRIPTION=$3

    if [ -n "$COVERAGE" ]
    then
        TEST="coverage run -p $COMMAND"
    else
        TEST="$COMMAND"
    fi
    OUTPUT=$($TEST 2>&1)
    if [ $? -gt 0 ]
    then
        echo "FAIL (test failure): $DESCRIPTION"
        $TEST
        exit 1;
    fi
    echo $OUTPUT | grep "Ran $TEST_COUNT test" > /dev/null
    if [ $? -gt 0 ]
    then
        echo "FAIL (count!=$TEST_COUNT): $DESCRIPTION"
        $TEST
        exit 1;
    else
        echo "PASS (count==$TEST_COUNT): $DESCRIPTION"
    fi

    # Check that we're hijacking the help correctly.
    $TEST --help 2>&1 | grep 'NOSE_DETAILED_ERRORS' > /dev/null
    if [ $? -gt 0 ]
    then
        echo "FAIL (--help): $DESCRIPTION"
        exit 1;
    else
        echo "PASS (  --help): $DESCRIPTION"
    fi
}

TESTAPP_COUNT=6

reset_env
django_test './manage.py test' $TESTAPP_COUNT 'normal settings'

DJANGO_VERSION=`./manage.py version | cut -d. -f1-2`
if [ "$DJANGO_VERSION" = "1.4" -o "$DJANGO_VERSION" = "1.5" -o "$DJANGO_VERSION" = "1.6" ]
then
    reset_env
    export USE_SOUTH=1
    django_test './manage.py test' $TESTAPP_COUNT 'with south in installed apps'
fi

reset_env
TEST_RUNNER="django_nose.run_tests"
django_test './manage.py test' $TESTAPP_COUNT 'django_nose.run_tests format'

reset_env
django_test 'testapp/runtests.py testapp.test_only_this' 1 'via run_tests API'

reset_env
NOSE_PLUGINS="testapp.plugins.SanityCheckPlugin"
django_test './manage.py test testapp/plugin_t' 1 'with plugins'

reset_env
django_test './manage.py test unittests' 4 'unittests'

reset_env
django_test './manage.py test unittests --testrunner=testapp.custom_runner.CustomNoseTestSuiteRunner' 4 'unittests with testrunner'

reset_env
export REUSE_DB=1
django_test './manage.py test' $TESTAPP_COUNT 'with REUSE_DB=1, call #1'
django_test './manage.py test' $TESTAPP_COUNT 'with REUSE_DB=1, call #2'


if ! [ $(version $PYTHONVERSION) \> $(version 3.0.0) ]
then
    # Python 3 doesn't support the hotshot profiler. See nose#842.
    reset_env
    django_test './manage.py test --with-profile' $TESTAPP_COUNT 'with profile plugin'
fi
