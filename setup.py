#!/usr/bin/env python
from __future__ import unicode_literals
import codecs
from io import open
import os
import re
import setuptools
from setuptools import setup, find_packages
import sys

PY2 = sys.version_info[0] == 2

# Borrowed from pip at https://github.com/pypa/pip/blob/62c27dee45625e1b63d1e023b0656310f276e050/setup.py#L11-L15
here = os.path.abspath(os.path.dirname(__file__))

def read(*parts):
    # intentionally *not* adding an encoding option to open, See:
    #   https://github.com/pypa/virtualenv/issues/201#issuecomment-3145690
    with open(os.path.join(here, *parts), 'r') as fp:
        return fp.read()


def get_version():
    version_file = read('moto', '__init__.py')
    version_match = re.search(r'^__version__ = [\'"]([^\'"]*)[\'"]',
                              version_file, re.MULTILINE)
    if version_match:
        return version_match.group(1)
    raise RuntimeError('Unable to find version string.')


install_requires = [
    "boto>=2.36.0",
    "boto3>=1.9.201",
    "botocore>=1.12.201",
    "cryptography>=2.3.0",
    "requests>=2.5",
    "xmltodict",
    "six>1.9",
    "werkzeug",
    "PyYAML>=5.1",
    "pytz",
    "python-dateutil<3.0.0,>=2.1",
    "python-jose[cryptography]>=3.1.0,<4.0.0",
    "docker>=2.5.1",
    "jsondiff>=1.1.2",
    "aws-xray-sdk!=0.96,>=0.93",
    "responses>=0.9.0",
    "idna<3,>=2.5",
    "cfn-lint>=0.4.0",
    "MarkupSafe<2.0",  # This is a Jinja2 dependency, 2.0.0a1 currently seems broken
]

#
# Avoid pins where they are not necessary.  These pins were introduced by the
# following commit for Py2 compatibility.  They are not required for non-Py2
# users.
#
#   https://github.com/mpenkov/moto/commit/00134d2df37bb4dcd5f447ef951d383bfec0903c
#
if PY2:
    install_requires += [
        #
        # This is an indirect dependency. Version 5.0.0 claims to be for
        # Py2.6+, but it really isn't.
        #
        # https://github.com/jaraco/configparser/issues/51
        #
        "configparser<5.0",
        "Jinja2<3.0.0,>=2.10.1",
        "mock<=3.0.5",
        "more-itertools==5.0.0",
        "setuptools==44.0.0",
        "sshpubkeys>=3.1.0,<4.0",
        "zipp==0.6.0",
    ]
else:
    install_requires += [
        "Jinja2>=2.10.1",
        "mock",
        "more-itertools",
        "setuptools",
        "sshpubkeys>=3.1.0",
        "zipp",
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
    version=get_version(),
    description='A library that allows your python tests to easily'
                ' mock out the boto library',
    long_description=read('README.md'),
    long_description_content_type='text/markdown',
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
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: Apache Software License",
        "Topic :: Software Development :: Testing",
    ],
    project_urls={
        "Documentation": "http://docs.getmoto.org/en/latest/",
    },
)
