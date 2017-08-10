#!/usr/bin/env python
"""
responses
=========

A utility library for mocking out the `requests` Python library.

:copyright: (c) 2015 David Cramer
:license: Apache 2.0
"""

import sys
import logging

from setuptools import setup
from setuptools.command.test import test as TestCommand
import pkg_resources


setup_requires = []

if 'test' in sys.argv:
    setup_requires.append('pytest')

install_requires = [
    'requests>=2.0',
    'cookies',
    'six',
]

tests_require = [
    'pytest',
    'coverage >= 3.7.1, < 5.0.0',
    'pytest-cov',
    'flake8',
]


extras_require = {
    ':python_version in "2.6, 2.7, 3.2"': ['mock'],
    'tests': tests_require,
}

try:
    if 'bdist_wheel' not in sys.argv:
        for key, value in extras_require.items():
            if key.startswith(':') and pkg_resources.evaluate_marker(key[1:]):
                install_requires.extend(value)
except Exception:
    logging.getLogger(__name__).exception(
        'Something went wrong calculating platform specific dependencies, so '
        "you're getting them all!"
    )
    for key, value in extras_require.items():
        if key.startswith(':'):
            install_requires.extend(value)


class PyTest(TestCommand):

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = ['test_responses.py']
        self.test_suite = True

    def run_tests(self):
        # import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main(self.test_args)
        sys.exit(errno)


setup(
    name='responses',
    version='0.6.0',
    author='David Cramer',
    description=(
        'A utility library for mocking out the `requests` Python library.'
    ),
    url='https://github.com/getsentry/responses',
    license='Apache 2.0',
    long_description=open('README.rst').read(),
    py_modules=['responses', 'test_responses'],
    zip_safe=False,
    install_requires=install_requires,
    extras_require=extras_require,
    tests_require=tests_require,
    setup_requires=setup_requires,
    cmdclass={'test': PyTest},
    include_package_data=True,
    classifiers=[
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development'
    ],
)
