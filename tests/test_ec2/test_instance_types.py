import boto3
import sure  # noqa # pylint: disable=unused-import
import pytest

from botocore.exceptions import ClientError

from moto import mock_ec2


@mock_ec2
def test_describe_instance_types():
    client = boto3.client("ec2", "us-east-1")
    instance_types = client.describe_instance_types()

    instance_types.should.have.key("InstanceTypes")
    instance_types["InstanceTypes"].should_not.be.empty
    instance_types["InstanceTypes"][0].should.have.key("InstanceType")
    instance_types["InstanceTypes"][0].should.have.key("MemoryInfo")
    instance_types["InstanceTypes"][0]["MemoryInfo"].should.have.key("SizeInMiB")


@mock_ec2
def test_describe_instance_types_filter_by_type():
    client = boto3.client("ec2", "us-east-1")
    instance_types = client.describe_instance_types(
        InstanceTypes=["t1.micro", "t2.nano"]
    )

    instance_types.should.have.key("InstanceTypes")
    instance_types["InstanceTypes"].should_not.be.empty
    instance_types["InstanceTypes"].should.have.length_of(2)
    instance_types["InstanceTypes"][0]["InstanceType"].should.be.within(
        ["t1.micro", "t2.nano"]
    )
    instance_types["InstanceTypes"][1]["InstanceType"].should.be.within(
        ["t1.micro", "t2.nano"]
    )


@mock_ec2
def test_describe_instance_types_unknown_type():
    client = boto3.client("ec2", "us-east-1")

    with pytest.raises(ClientError) as err:
        client.describe_instance_types(InstanceTypes=["t1.non_existent"])
        err.response["Error"]["Code"].should.equal("ValidationException")
        err.response["Error"]["Message"].split(":")[0].should.look_like(
            "The instance type '{'t1.non_existent'}' does not exist"
        )
        err.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
