#!/usr/bin/env python
from __future__ import unicode_literals
from setuptools import setup, find_packages

install_requires = [
    "Jinja2",
    "boto",
    "dicttoxml",
    "flask",
    "httpretty>=0.6.1",
    "requests",
    "xmltodict",
    "six",
    "werkzeug",
]

import sys

if sys.version_info < (2, 7):
    # No buildint OrderedDict before 2.7
    install_requires.append('ordereddict')

setup(
    name='moto',
    version='0.3.7',
    description='A library that allows your python tests to easily'
                ' mock out the boto library',
    author='Steve Pulec',
    author_email='spulec@gmail',
    url='https://github.com/spulec/moto',
    entry_points={
        'console_scripts': [
            'moto_server = moto.server:main',
        ],
    },
    packages=find_packages(exclude=("tests", "tests.*")),
    install_requires=install_requires,
    license="Apache",
    test_suite="tests",
    classifiers=[
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.3",
        "License :: OSI Approved :: Apache Software License",
        "Topic :: Software Development :: Testing",
    ],
)
