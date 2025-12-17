import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from tests import EXAMPLE_AMI_ID


@mock_aws
def test_console_output():
    conn = boto3.resource("ec2", "us-east-1")
    instances = conn.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)

    resp = instances[0].console_output()
    output = resp.get("Output")
    assert output.startswith("Linux version")


@mock_aws
def test_console_output_without_instance():
    client = boto3.client("ec2", "us-east-1")

    with pytest.raises(ClientError) as ex:
        client.get_console_output(InstanceId="i-1234abcd")
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.value.response["ResponseMetadata"]["RequestId"] is not None
    assert ex.value.response["Error"]["Code"] == "InvalidInstanceID.NotFound"
