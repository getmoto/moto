#!/usr/bin/env python
from io import open
import os
import re
from setuptools import setup, find_packages
import sys
import moto.__init__ as service_list

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
    "werkzeug",
    "pytz",
    "python-dateutil<3.0.0,>=2.1",
    "responses>=0.9.0",
    "MarkupSafe!=2.0.0a1",  # This is a Jinja2 dependency, 2.0.0a1 currently seems broken
    "Jinja2>=2.10.1",
    "importlib_metadata ; python_version < '3.8'",
]

_dep_PyYAML = "PyYAML>=5.1"
_dep_python_jose = "python-jose[cryptography]>=3.1.0,<4.0.0"
_dep_python_jose_ecdsa_pin = (
    "ecdsa!=0.15"  # https://github.com/spulec/moto/pull/3263#discussion_r477404984
)
_dep_dataclasses = "dataclasses; python_version < '3.7'"
_dep_docker = "docker>=2.5.1"
_dep_graphql = "graphql-core"
_dep_jsondiff = "jsondiff>=1.1.2"
_dep_aws_xray_sdk = "aws-xray-sdk!=0.96,>=0.93"
_dep_idna = "idna<4,>=2.5"
_dep_cfn_lint = "cfn-lint>=0.4.0"
_dep_sshpubkeys = "sshpubkeys>=3.1.0"
_setuptools = "setuptools"

all_extra_deps = [
    _dep_PyYAML,
    _dep_python_jose,
    _dep_python_jose_ecdsa_pin,
    _dep_docker,
    _dep_graphql,
    _dep_jsondiff,
    _dep_aws_xray_sdk,
    _dep_idna,
    _dep_cfn_lint,
    _dep_sshpubkeys,
    _setuptools,
]
all_server_deps = all_extra_deps + ["flask", "flask-cors"]

extras_per_service = {}
for service_name in [
    service[5:]
    for service in dir(service_list)
    if service.startswith("mock_") and not service == "mock_all"
]:
    extras_per_service[service_name] = []
extras_per_service.update(
    {
        "apigateway": [_dep_python_jose, _dep_python_jose_ecdsa_pin],
        "appsync": [_dep_graphql],
        "awslambda": [_dep_docker],
        "batch": [_dep_docker],
        "cloudformation": [_dep_docker, _dep_PyYAML, _dep_cfn_lint],
        "cognitoidp": [_dep_python_jose, _dep_python_jose_ecdsa_pin],
        "ec2": [_dep_sshpubkeys],
        "iotdata": [_dep_jsondiff],
        "s3": [_dep_PyYAML],
        "ses": [],
        "sns": [],
        "sqs": [],
        "ssm": [_dep_PyYAML, _dep_dataclasses],
        # XRay module uses pkg_resources, but doesn't have an explicit
        # dependency listed.  This should be fixed in the next version:
        # https://github.com/aws/aws-xray-sdk-python/issues/305
        "xray": [_dep_aws_xray_sdk, _setuptools],
    }
)

# When a Table has a Stream, we'll always need to import AWSLambda to search for a corresponding function to send the table data to
extras_per_service["dynamodb2"] = extras_per_service["awslambda"]
extras_per_service["dynamodbstreams"] = extras_per_service["awslambda"]
# EFS depends on EC2 to find subnets etc
extras_per_service["efs"] = extras_per_service["ec2"]
# DirectoryService needs EC2 to verify VPCs and subnets.
extras_per_service["ds"] = extras_per_service["ec2"]
extras_per_service["route53resolver"] = extras_per_service["ec2"]
extras_require = {
    "all": all_extra_deps,
    "server": all_server_deps,
}

extras_require.update(extras_per_service)


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
    entry_points={"console_scripts": ["moto_server = moto.server:main"]},
    packages=find_packages(exclude=("tests", "tests.*")),
    install_requires=install_requires,
    extras_require=extras_require,
    include_package_data=True,
    license="Apache",
    test_suite="tests",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "License :: OSI Approved :: Apache Software License",
        "Topic :: Software Development :: Testing",
    ],
    project_urls={"Documentation": "http://docs.getmoto.org/en/latest/"},
)
