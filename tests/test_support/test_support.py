from __future__ import unicode_literals

import boto3
import sure  # noqa
from moto import mock_support


@mock_support
def test_describe_trusted_advisor_checks():
    """
    104 checks are listed under trusted advisor currently
    """
    client = boto3.client("support", "us-east-1")
    response = client.describe_trusted_advisor_checks(language="en",)

    response["checks"].should.be.length_of(104)
