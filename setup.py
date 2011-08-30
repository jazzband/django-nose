import os
from setuptools import setup, find_packages

ROOT = os.path.abspath(os.path.dirname(__file__))

setup(
    name='django-nose',
    version='0.1.3',
    description='Django test runner that uses nose.',
    long_description=open(os.path.join(ROOT, 'README.rst')).read(),
    author='Jeff Balogh',
    author_email='me@jeffbalogh.org',
    url='http://github.com/jbalogh/django-nose',
    license='BSD',
    packages=find_packages(exclude=['testapp','testapp/*']),
    include_package_data=True,
    zip_safe=False,
    install_requires=['nose'],
    entry_points="""
        [nose.plugins.0.10]
        fixture_bundler = django_nose.fixture_bundling:FixtureBundlingPlugin
        """,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ]
)
