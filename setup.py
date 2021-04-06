#!/usr/bin/env python
from __future__ import unicode_literals
import codecs
from io import open
import os
import re
import setuptools
from setuptools import setup, find_packages
import sys

# Borrowed from pip at https://github.com/pypa/pip/blob/62c27dee45625e1b63d1e023b0656310f276e050/setup.py#L11-L15
here = os.path.abspath(os.path.dirname(__file__))


def read(*parts):
    # intentionally *not* adding an encoding option to open, See:
    #   https://github.com/pypa/virtualenv/issues/201#issuecomment-3145690
    with open(os.path.join(here, *parts), "r") as fp:
        return fp.read()


def get_version():
    version_file = read("moto", "__init__.py")
    version_match = re.search(
        r'^__version__ = [\'"]([^\'"]*)[\'"]', version_file, re.MULTILINE
    )
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


install_requires = [
    "boto3>=1.9.201",
    "botocore>=1.12.201",
    "cryptography>=3.3.1",
    "requests>=2.5",
    "xmltodict",
    "six>1.9",
    "werkzeug",
    "pytz",
    "python-dateutil<3.0.0,>=2.1",
    "responses>=0.9.0",
    "MarkupSafe<2.0",  # This is a Jinja2 dependency, 2.0.0a1 currently seems broken
]

#
# Avoid pins where they are not necessary.  These pins were introduced by the
# following commit for Py2 compatibility.  They are not required for non-Py2
# users.
#
#   https://github.com/mpenkov/moto/commit/00134d2df37bb4dcd5f447ef951d383bfec0903c
#
install_requires += [
    #
    # This is an indirect dependency. Version 5.0.0 claims to be for
    # Py2.6+, but it really isn't.
    #
    # https://github.com/jaraco/configparser/issues/51
    #
    "configparser<5.0; python_version < '3'",
    "Jinja2>=2.10.1",
    "Jinja2<3.0.0; python_version < '3'",
    "mock<=3.0.5; python_version < '3'",
    "more-itertools",
    "more-itertools==5.0.0; python_version < '3'",
    # Indirect - Py2 works with 4.5, breaks with 4.7, but officially only supported by 4.0
    "rsa<=4.0; python_version < '3'",
    "setuptools",
    "setuptools==44.0.0; python_version < '3'",
    "zipp",
    "zipp==0.6.0; python_version < '3'",
]

_dep_PyYAML = "PyYAML>=5.1"
_dep_python_jose = "python-jose[cryptography]>=3.1.0,<4.0.0"
_dep_python_jose_ecdsa_pin = (
    "ecdsa<0.15"  # https://github.com/spulec/moto/pull/3263#discussion_r477404984
)
_dep_docker = "docker>=2.5.1"
_dep_jsondiff = "jsondiff>=1.1.2"
_dep_aws_xray_sdk = "aws-xray-sdk!=0.96,>=0.93"
_dep_idna = "idna<3,>=2.5"
_dep_cfn_lint = "cfn-lint>=0.4.0"
_dep_decorator = "decorator<=4.4.2; python_version<'3'"  # Transitive dependency - last version that supports py2.7
_dep_sshpubkeys_py2 = "sshpubkeys==3.1.0; python_version<'3'"
_dep_sshpubkeys_py3 = "sshpubkeys>=3.1.0; python_version>'3'"

all_extra_deps = [
    _dep_PyYAML,
    _dep_python_jose,
    _dep_python_jose_ecdsa_pin,
    _dep_docker,
    _dep_jsondiff,
    _dep_aws_xray_sdk,
    _dep_idna,
    _dep_cfn_lint,
    _dep_decorator,
    _dep_sshpubkeys_py2,
    _dep_sshpubkeys_py3,
]
all_server_deps = all_extra_deps + ["flask", "flask-cors"]

# TODO: do we want to add ALL services here?
# i.e. even those without extra dependencies.
# Would be good for future-compatibility, I guess.
extras_per_service = {
    "apigateway": [_dep_python_jose, _dep_python_jose_ecdsa_pin],
    "awslambda": [_dep_docker],
    "batch": [_dep_docker],
    "cloudformation": [_dep_docker, _dep_PyYAML, _dep_cfn_lint, _dep_decorator],
    "cognitoidp": [_dep_python_jose, _dep_python_jose_ecdsa_pin],
    "dynamodb2": [_dep_docker],
    "dynamodbstreams": [_dep_docker],
    "ec2": [_dep_docker, _dep_sshpubkeys_py2, _dep_sshpubkeys_py3],
    "iotdata": [_dep_jsondiff],
    "s3": [_dep_PyYAML],
    "ses": [_dep_docker],
    "sns": [_dep_docker],
    "sqs": [_dep_docker],
    "ssm": [_dep_docker, _dep_PyYAML, _dep_cfn_lint, _dep_decorator],
    "xray": [_dep_aws_xray_sdk],
}
extras_require = {
    "all": all_extra_deps,
    "server": all_server_deps,
}

extras_require.update(extras_per_service)

# https://hynek.me/articles/conditional-python-dependencies/
if int(setuptools.__version__.split(".", 1)[0]) < 18:
    if sys.version_info[0:2] < (3, 3):
        install_requires.append("backports.tempfile")
else:
    extras_require[":python_version<'3.3'"] = ["backports.tempfile"]


setup(
    name="moto",
    version=get_version(),
    description="A library that allows your python tests to easily"
    " mock out the boto library",
    long_description=read("README.md"),
    long_description_content_type="text/markdown",
    author="Steve Pulec",
    author_email="spulec@gmail.com",
    url="https://github.com/spulec/moto",
    entry_points={
        "console_scripts": [
            "moto_server = moto.server:main",
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
