import pytest

import boto
import boto3
from boto.exception import EC2ResponseError
import sure  # noqa # pylint: disable=unused-import
from botocore.exceptions import ClientError

from moto import mock_ec2_deprecated, mock_ec2
from tests import EXAMPLE_AMI_ID


# Has boto3 equivalent
@mock_ec2_deprecated
def test_console_output():
    conn = boto.connect_ec2("the_key", "the_secret")
    reservation = conn.run_instances(EXAMPLE_AMI_ID)
    instance_id = reservation.instances[0].id
    output = conn.get_console_output(instance_id)
    output.output.should_not.equal(None)


# Has boto3 equivalent
@mock_ec2_deprecated
def test_console_output_without_instance():
    conn = boto.connect_ec2("the_key", "the_secret")

    with pytest.raises(EC2ResponseError) as cm:
        conn.get_console_output("i-1234abcd")
    cm.value.error_code.should.equal("InvalidInstanceID.NotFound")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none


@mock_ec2
def test_console_output_boto3():
    conn = boto3.resource("ec2", "us-east-1")
    instances = conn.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)

    output = instances[0].console_output()
    output.get("Output").should_not.equal(None)


@mock_ec2
def test_console_output_without_instance_boto3():
    client = boto3.client("ec2", "us-east-1")

    with pytest.raises(ClientError) as ex:
        client.get_console_output(InstanceId="i-1234abcd")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"]["RequestId"].shouldnt.be.none
    ex.value.response["Error"]["Code"].should.equal("InvalidInstanceID.NotFound")
