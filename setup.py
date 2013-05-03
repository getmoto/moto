#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name='moto',
    version='0.1.5',
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
    packages=find_packages(),
    install_requires=[
        "boto",
        "flask",
        "httpretty==0.6.0a",
        "Jinja2",
    ],
    dependency_links=[
        "https://github.com/gabrielfalcao/HTTPretty/tarball/2347df40a3a3cd00e73f0353f5ea2670ad3405c1#egg=httpretty-0.6.0a",
    ],
)
