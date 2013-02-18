#!/usr/bin/env python

import sys
from setuptools import setup, find_packages

setup(
    name='moto',
    version='0.0.1',
    description='Moto is a library that allows your python tests to easily mock out the boto library',
    author='Steve Pulec',
    author_email='spulec@gmail',
    url='https://github.com/spulec/moto',
    packages=find_packages()
)