.PHONY: clean clean-build clean-pyc clean-test qa lint coverage jslint qa-all install-jslint test test-all coverage-console release sdist

help:
	@echo "clean - remove all artifacts"
	@echo "clean-build - remove build artifacts"
	@echo "clean-pyc - remove Python file artifacts"
	@echo "clean-test - remove test and coverage artifacts"
	@echo "coverage - check code coverage quickly with the default Python"
	@echo "lint - check style with flake8"
	@echo "qa - run linters and test coverage"
	@echo "qa-all - run QA plus tox and packaging"
	@echo "release - package and upload a release"
	@echo "sdist - package"
	@echo "test - run tests quickly with the default Python"
	@echo "test-all - run tests on every Python version with tox"
	@echo "test-release - upload a release to the PyPI test server

clean: clean-build clean-pyc clean-test

qa: lint coverage jslint

qa-all: qa sdist test-all

clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr *.egg-info

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test:
	rm -fr .tox/
	rm -f .coverage
	rm -fr htmlcov/

lint:
	flake8 .

jslint:
	if type jslint >/dev/null 2>&1 ; then jslint django_nose/static/js/*; else echo "jslint not installed. To install node and jshint, use 'make install_jslint"; fi

install-jslint:
	if [ -z "$$VIRTUAL_ENV" ]; then echo "Run inside a virtualenv"; exit 1; fi
	mkdir -p .node_src_tmp
	cd .node_src_tmp && curl http://nodejs.org/dist/node-latest.tar.gz | tar xvz && cd node-v* && ./configure --prefix=$$VIRTUAL_ENV && make install
	npm install -g jslint
	rm -rf .node_src_tmp

test:
	./manage.py test

test-all:
	tox --skip-missing-interpreters

coverage-console:
	coverage erase
	COVERAGE=1 ./runtests.sh
	coverage combine
	coverage report -m

coverage: coverage-console
	coverage html
	open htmlcov/index.html

release: clean
	python setup.py sdist bdist_wheel upload
	python -m webbrowser -n https://testpypi.python.org/pypi/django-nose

test-release:
	python setup.py register -r https://testpypi.python.org/pypi
	python setup.py sdist bdist_wheel upload -r https://testpypi.python.org/pypi
	python -m webbrowser -n https://testpypi.python.org/pypi/django-nose

sdist: clean
	python setup.py sdist
	ls -l dist
	check-manifest
	pyroma dist/`ls -t dist | head -n1`
