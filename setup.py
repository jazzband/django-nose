from setuptools import setup, find_packages


setup(
    name='django-nose',
    version='0.1',
    description='Django test runner that uses nose.',
    long_description=open('README.rst').read(),
    author='Jeff Balogh',
    author_email='me@jeffbalogh.org',
    url='http://github.com/jbalogh/django-nose',
    license='BSD',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=['nose'],
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
