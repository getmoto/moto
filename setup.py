#!/usr/bin/env python
from __future__ import unicode_literals
import setuptools
from setuptools import setup, find_packages
import sys


install_requires = [
    "Jinja2>=2.7.3",
    "boto>=2.36.0",
    "boto3>=1.6.16,<1.8",
    "botocore>=1.9.16,<1.11",
    "cookies",
    "cryptography>=2.0.0",
    "requests>=2.5",
    "xmltodict",
    "six>1.9",
    "werkzeug",
    "pyaml",
    "pytz",
    "python-dateutil<3.0.0,>=2.1",
    "python-jose<3.0.0",
    "mock",
    "docker>=2.5.1",
    "jsondiff==1.1.1",
    "aws-xray-sdk<0.96,>=0.93",
    "responses>=0.9.0",
]

extras_require = {
    'server': ['flask'],
}

# https://hynek.me/articles/conditional-python-dependencies/
if int(setuptools.__version__.split(".", 1)[0]) < 18:
    if sys.version_info[0:2] < (3, 3):
        install_requires.append("backports.tempfile")
else:
    extras_require[":python_version<'3.3'"] = ["backports.tempfile"]


setup(
    name='moto',
    version='1.3.6',
    description='A library that allows your python tests to easily'
                ' mock out the boto library',
    author='Steve Pulec',
    author_email='spulec@gmail.com',
    url='https://github.com/spulec/moto',
    entry_points={
        'console_scripts': [
            'moto_server = moto.server:main',
        ],
    },
    packages=find_packages(exclude=("tests", "tests.*")),
    install_requires=install_requires,
    extras_require=extras_require,
    include_package_data=True,
    license="Apache",
    test_suite="tests",
    classifiers=[
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "License :: OSI Approved :: Apache Software License",
        "Topic :: Software Development :: Testing",
    ],
)
