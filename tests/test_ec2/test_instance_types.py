from __future__ import unicode_literals

import boto3
import sure  # noqa

from moto import mock_ec2


@mock_ec2
def test_describe_instance_types():
    client = boto3.client("ec2", "us-east-1")
    instance_types = client.describe_instance_types()

    instance_types.get("InstanceTypes").should_not.equal(None)
    instance_types["InstanceTypes"].should_not.be.empty
    instance_types["InstanceTypes"][0].should.have.key("InstanceType")
