import boto3
import sure  # noqa # pylint: disable=unused-import
import pytest

from botocore.exceptions import ClientError

from moto import mock_ec2


@mock_ec2
def test_describe_instance_types():
    client = boto3.client("ec2", "us-east-1")
    instance_types = client.describe_instance_types()

    instance_types.should.have.key("InstanceTypes").be.a(list)
    len(instance_types["InstanceTypes"]).should.be.greater_than(0)
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
    instance_types["InstanceTypes"].should.have.length_of(2)
    instance_types["InstanceTypes"][0]["InstanceType"].should.be.within(
        ["t1.micro", "t2.nano"]
    )
    instance_types["InstanceTypes"][1]["InstanceType"].should.be.within(
        ["t1.micro", "t2.nano"]
    )


@mock_ec2
def test_describe_instance_types_gpu_instance_types():
    client = boto3.client("ec2", "us-east-1")
    instance_types = client.describe_instance_types(
        InstanceTypes=["p3.2xlarge", "g4ad.8xlarge"]
    )

    instance_types.should.have.key("InstanceTypes")
    instance_types["InstanceTypes"].should.have.length_of(2)
    instance_types["InstanceTypes"][0].should.have.key("GpuInfo")
    instance_types["InstanceTypes"][1].should.have.key("GpuInfo")

    instance_type_to_gpu_info = {
        instance_info["InstanceType"]: instance_info["GpuInfo"]
        for instance_info in instance_types["InstanceTypes"]
    }
    assert instance_type_to_gpu_info == {
        "g4ad.8xlarge": {
            "Gpus": [
                {
                    "Count": 2,
                    "Manufacturer": "AMD",
                    "MemoryInfo": {"SizeInMiB": 8192},
                    "Name": "Radeon Pro V520",
                }
            ],
            "TotalGpuMemoryInMiB": 16384,
        },
        "p3.2xlarge": {
            "Gpus": [
                {
                    "Count": 1,
                    "Manufacturer": "NVIDIA",
                    "MemoryInfo": {"SizeInMiB": 16384},
                    "Name": "V100",
                }
            ],
            "TotalGpuMemoryInMiB": 16384,
        },
    }


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


@mock_ec2
def test_describe_instance_types_filter_by_vcpus():
    client = boto3.client("ec2", "us-east-1")
    instance_types = client.describe_instance_types(
        Filters=[{"Name": "vcpu-info.default-vcpus", "Values": ["1", "2"]}]
    )

    instance_types.should.have.key("InstanceTypes")
    types = [
        instance_type["InstanceType"]
        for instance_type in instance_types["InstanceTypes"]
    ]
    types.should.contain("t1.micro")
    types.should.contain("t2.nano")

    # not contain
    types.should_not.contain("m5d.xlarge")


@mock_ec2
def test_describe_instance_types_filter_by_memory():
    client = boto3.client("ec2", "us-east-1")
    instance_types = client.describe_instance_types(
        Filters=[{"Name": "memory-info.size-in-mib", "Values": ["512"]}]
    )

    instance_types.should.have.key("InstanceTypes")
    types = [
        instance_type["InstanceType"]
        for instance_type in instance_types["InstanceTypes"]
    ]
    types.should.contain("t4g.nano")

    # not contain
    types.should_not.contain("m5d.xlarge")


@mock_ec2
def test_describe_instance_types_filter_by_bare_metal():
    client = boto3.client("ec2", "us-east-1")
    instance_types = client.describe_instance_types(
        Filters=[{"Name": "bare-metal", "Values": ["true"]}]
    )

    instance_types.should.have.key("InstanceTypes")
    types = [
        instance_type["InstanceType"]
        for instance_type in instance_types["InstanceTypes"]
    ]
    types.should.contain("a1.metal")

    # not contain
    types.should_not.contain("t1.micro")


@mock_ec2
def test_describe_instance_types_filter_by_burstable_performance_supported():
    client = boto3.client("ec2", "us-east-1")
    instance_types = client.describe_instance_types(
        Filters=[{"Name": "burstable-performance-supported", "Values": ["true"]}]
    )

    instance_types.should.have.key("InstanceTypes")
    types = [
        instance_type["InstanceType"]
        for instance_type in instance_types["InstanceTypes"]
    ]
    types.should.contain("t2.micro")

    # not contain
    types.should_not.contain("t1.micro")


@mock_ec2
def test_describe_instance_types_filter_by_current_generation():
    client = boto3.client("ec2", "us-east-1")
    instance_types = client.describe_instance_types(
        Filters=[{"Name": "current-generation", "Values": ["true"]}]
    )

    instance_types.should.have.key("InstanceTypes")
    types = [
        instance_type["InstanceType"]
        for instance_type in instance_types["InstanceTypes"]
    ]
    types.should.contain("t2.micro")

    # not contain
    types.should_not.contain("t1.micro")
