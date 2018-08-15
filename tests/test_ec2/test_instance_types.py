from __future__ import unicode_literals
# Ensure 'assert_raises' context manager support for Python 2.6
import tests.backport_assert_raises
from nose.tools import assert_raises

import base64
import datetime
import ipaddress

import six
import boto
import boto3
from boto.ec2.instance import Reservation, InstanceAttribute
from boto.exception import EC2ResponseError, EC2ResponseError
from botocore.exceptions import ClientError
from freezegun import freeze_time
import sure  # noqa

from moto import mock_ec2_deprecated, mock_ec2
from tests.helpers import requires_boto_gte


@mock_ec2
def test_run_instances_valid_instance_type():
    client = boto3.client("ec2", region_name="us-east-2")

    image_id = "ami-1234abcd"

    instance_type = "t2.nano"

    client.run_instances(InstanceType=instance_type, ImageId=image_id, MinCount=1, MaxCount=1)

    describe_instances = client.describe_instances()

    describe_instances["Reservations"][0]["Instances"][0]["InstanceType"].should.equal("t2.nano")


@mock_ec2
def test_run_instances_invalid_instance_type():
    client = boto3.client("ec2", region_name="us-east-2")

    image_id = "ami-1234abcd"

    # this may exist in the future, so this could be valid in the year 2050 or something
    instance_type = "t300.nano"

    with assert_raises(ClientError) as err:
        client.run_instances(InstanceType=instance_type, ImageId=image_id, MinCount=1, MaxCount=1)
    
    e = err.exception
    e.response["Error"]["Code"].should.equal("InvalidParameterValue")


@mock_ec2
def test_run_instances_invalid_instance_type2():
    client = boto3.client("ec2", region_name="us-east-2")

    image_id = "ami-1234abcd"

    # this may exist in the future, so this could be valid in the year 2050 or something
    instance_type = "t6P.nano"

    with assert_raises(ClientError) as err:
        client.run_instances(InstanceType=instance_type, ImageId=image_id, MinCount=1, MaxCount=1)
    
    e = err.exception
    e.response["Error"]["Code"].should.equal("InvalidParameterValue")


@mock_ec2
def test_default_run_instances():
    client = boto3.client("ec2", region_name="us-east-2")

    image_id = "ami-1234abcd"

    client.run_instances(ImageId=image_id, MinCount=1, MaxCount=1)

    describe_instances = client.describe_instances()

    # default instance type is m1.small
    describe_instances["Reservations"][0]["Instances"][0]["InstanceType"].should.equal("m1.small")


@mock_ec2
def test_run_instances_invalid_instance_type_format():
    client = boto3.client("ec2", region_name="us-east-2")

    image_id = "ami-1234abcd"

    # not of the format instance_family.instance_size
    instance_type = "p5large"

    with assert_raises(ClientError) as err:
        client.run_instances(InstanceType=instance_type, ImageId=image_id, MinCount=1, MaxCount=1)
    
    e = err.exception
    e.response["Error"]["Code"].should.equal("InvalidParameterValue")


@mock_ec2
def test_run_instances_special_instance_type():
    client = boto3.client("ec2", region_name="us-east-2")

    image_id = "ami-1234abcd"

    instance_type="c5d.18xlarge"

    client.run_instances(InstanceType=instance_type, ImageId=image_id, MinCount=1, MaxCount=1)

    describe_instances = client.describe_instances()

    # this is a valid instance type, but the format is a little different
    describe_instances["Reservations"][0]["Instances"][0]["InstanceType"].should.equal("c5d.18xlarge")
    
