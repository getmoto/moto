import boto3
import pytest

from botocore.exceptions import ClientError

from moto import mock_ec2


@mock_ec2
def test_describe_instance_types():
    client = boto3.client("ec2", "us-east-1")
    instance_types = client.describe_instance_types()

    assert len(instance_types["InstanceTypes"]) > 0
    assert "InstanceType" in instance_types["InstanceTypes"][0]
    assert "SizeInMiB" in instance_types["InstanceTypes"][0]["MemoryInfo"]


@mock_ec2
def test_describe_instance_types_filter_by_type():
    client = boto3.client("ec2", "us-east-1")
    instance_types = client.describe_instance_types(
        InstanceTypes=["t1.micro", "t2.nano"]
    )

    assert "InstanceTypes" in instance_types
    assert len(instance_types["InstanceTypes"]) == 2
    assert instance_types["InstanceTypes"][0]["InstanceType"] in ["t1.micro", "t2.nano"]
    assert instance_types["InstanceTypes"][1]["InstanceType"] in ["t1.micro", "t2.nano"]


@mock_ec2
def test_describe_instance_types_gpu_instance_types():
    client = boto3.client("ec2", "us-east-1")
    instance_types = client.describe_instance_types(
        InstanceTypes=["p3.2xlarge", "g4ad.8xlarge"]
    )

    assert len(instance_types["InstanceTypes"]) == 2
    assert "GpuInfo" in instance_types["InstanceTypes"][0]
    assert "GpuInfo" in instance_types["InstanceTypes"][1]

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

    with pytest.raises(ClientError) as exc_info:
        client.describe_instance_types(InstanceTypes=["t1.non_existent"])

    assert exc_info.value.response["Error"]["Code"] == "InvalidInstanceType"
    assert (
        exc_info.value.response["Error"]["Message"]
        == "The following supplied instance types do not exist: [t1.non_existent]"
    )
    assert exc_info.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400


@mock_ec2
def test_describe_instance_types_filter_by_vcpus():
    client = boto3.client("ec2", "us-east-1")
    instance_types = client.describe_instance_types(
        Filters=[{"Name": "vcpu-info.default-vcpus", "Values": ["1", "2"]}]
    )

    types = [
        instance_type["InstanceType"]
        for instance_type in instance_types["InstanceTypes"]
    ]
    assert "t1.micro" in types
    assert "t2.nano" in types

    # not contain
    assert "m5d.xlarge" not in types


@mock_ec2
def test_describe_instance_types_filter_by_memory():
    client = boto3.client("ec2", "us-east-1")
    instance_types = client.describe_instance_types(
        Filters=[{"Name": "memory-info.size-in-mib", "Values": ["512"]}]
    )

    types = [
        instance_type["InstanceType"]
        for instance_type in instance_types["InstanceTypes"]
    ]
    assert "t4g.nano" in types

    # not contain
    assert "m5d.xlarge" not in types


@mock_ec2
def test_describe_instance_types_filter_by_bare_metal():
    client = boto3.client("ec2", "us-east-1")
    instance_types = client.describe_instance_types(
        Filters=[{"Name": "bare-metal", "Values": ["true"]}]
    )

    types = [
        instance_type["InstanceType"]
        for instance_type in instance_types["InstanceTypes"]
    ]
    assert "a1.metal" in types

    # not contain
    assert "t1.micro" not in types


@mock_ec2
def test_describe_instance_types_filter_by_burstable_performance_supported():
    client = boto3.client("ec2", "us-east-1")
    instance_types = client.describe_instance_types(
        Filters=[{"Name": "burstable-performance-supported", "Values": ["true"]}]
    )

    types = [
        instance_type["InstanceType"]
        for instance_type in instance_types["InstanceTypes"]
    ]
    assert "t2.micro" in types

    # not contain
    assert "t1.micro" not in types


@mock_ec2
def test_describe_instance_types_filter_by_current_generation():
    client = boto3.client("ec2", "us-east-1")
    instance_types = client.describe_instance_types(
        Filters=[{"Name": "current-generation", "Values": ["true"]}]
    )

    types = [
        instance_type["InstanceType"]
        for instance_type in instance_types["InstanceTypes"]
    ]
    assert "t2.micro" in types

    # not contain
    assert "t1.micro" not in types


@mock_ec2
def test_describe_instance_types_small_instances():
    client = boto3.client("ec2", "us-east-1")
    instance_types = client.describe_instance_types(Filters=[
        {"Name": "bare-metal", "Values": ["false"]},
        {"Name": "current-generation", "Values": ["true"]},
        {"Name": "vcpu-info.default-cores", "Values": ["1"]},
        {"Name": "memory-info.size-in-mib", "Values": ["512", "1024"]},
        {"Name": "vcpu-info.valid-threads-per-core", "Values": ["1"]},
    ])  # fmt: skip

    types = set(t["InstanceType"] for t in instance_types["InstanceTypes"])
    assert types == {"t3.nano", "t3.micro", "t3a.nano", "t3a.micro"}


@mock_ec2
def test_describe_instance_types_invalid_filter():
    client = boto3.client("ec2", "us-east-1")

    with pytest.raises(ClientError) as exc_info:
        client.describe_instance_types(
            Filters=[{"Name": "spam", "Values": ["eggs"]}],
        )

    assert exc_info.value.response["Error"]["Code"] == "InvalidParameterValue"
    assert (
        exc_info.value.response["Error"]["Message"].split(":")[0]
        == "The filter 'spam' is invalid"
    )
    assert exc_info.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
