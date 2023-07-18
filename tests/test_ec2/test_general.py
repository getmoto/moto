import pytest

import boto3
from botocore.exceptions import ClientError

from moto import mock_ec2
from tests import EXAMPLE_AMI_ID


@mock_ec2
def test_console_output():
    conn = boto3.resource("ec2", "us-east-1")
    instances = conn.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)

    output = instances[0].console_output()
    assert output.get("Output") is not None


@mock_ec2
def test_console_output_without_instance():
    client = boto3.client("ec2", "us-east-1")

    with pytest.raises(ClientError) as ex:
        client.get_console_output(InstanceId="i-1234abcd")
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.value.response["ResponseMetadata"]["RequestId"] is not None
    assert ex.value.response["Error"]["Code"] == "InvalidInstanceID.NotFound"
