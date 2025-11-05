import boto3

from moto import mock_aws


@mock_aws
def test_describe_reserved_instances_offerings_basic():
    client = boto3.client("ec2", region_name="us-east-1")

    resp = client.describe_reserved_instances_offerings()

    assert "ReservedInstancesOfferings" in resp
    offerings = resp["ReservedInstancesOfferings"]
    assert isinstance(offerings, list)
    assert len(offerings) > 0
    first = offerings[0]
    assert "ReservedInstancesOfferingId" in first
    assert "InstanceType" in first


@mock_aws
def test_describe_reserved_instances_offerings_filter_instance_type():
    client = boto3.client("ec2", region_name="us-east-1")

    resp = client.describe_reserved_instances_offerings(
        Filters=[{"Name": "instance-type", "Values": ["t2.micro"]}]
    )
    offerings = resp["ReservedInstancesOfferings"]
    assert len(offerings) > 0
    assert all(o["InstanceType"] == "t2.micro" for o in offerings)


@mock_aws
def test_describe_reserved_instances_offerings_filter_az():
    client = boto3.client("ec2", region_name="us-east-1")

    # Choose a known AZ from mapping
    target_az = "us-east-1a"
    resp = client.describe_reserved_instances_offerings(
        Filters=[{"Name": "availability-zone", "Values": [target_az]}]
    )
    offerings = resp["ReservedInstancesOfferings"]
    assert len(offerings) > 0
    assert all(o.get("AvailabilityZone") == target_az for o in offerings)


@mock_aws
def test_describe_reserved_instances_offerings_filter_product_description():
    client = boto3.client("ec2", region_name="us-east-1")

    resp = client.describe_reserved_instances_offerings(
        Filters=[{"Name": "product-description", "Values": ["Linux/UNIX"]}]
    )
    offerings = resp["ReservedInstancesOfferings"]
    assert len(offerings) > 0
    assert all(o.get("ProductDescription") == "Linux/UNIX" for o in offerings)
