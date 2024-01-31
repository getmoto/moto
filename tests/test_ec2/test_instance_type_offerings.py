import boto3

from moto import mock_aws


@mock_aws
def test_describe_instance_type_offerings():
    client = boto3.client("ec2", "us-east-1")
    offerings = client.describe_instance_type_offerings()

    assert len(offerings["InstanceTypeOfferings"]) > 0
    assert "InstanceType" in offerings["InstanceTypeOfferings"][0]
    assert "Location" in offerings["InstanceTypeOfferings"][0]
    assert "LocationType" in offerings["InstanceTypeOfferings"][0]


@mock_aws
def test_describe_instance_type_offering_filter_by_type():
    client = boto3.client("ec2", "us-east-1")

    # Verify offerings of a specific instance type
    offerings = client.describe_instance_type_offerings(
        Filters=[{"Name": "instance-type", "Values": ["t2.nano"]}]
    )

    assert "InstanceTypeOfferings" in offerings
    offerings = offerings["InstanceTypeOfferings"]
    assert len(offerings) == 1
    assert offerings[0]["InstanceType"] == "t2.nano"
    assert offerings[0]["Location"] == "us-east-1"

    # Verify offerings of that instance type per availibility zone
    offerings = client.describe_instance_type_offerings(
        LocationType="availability-zone",
        Filters=[{"Name": "instance-type", "Values": ["t2.nano"]}],
    )
    assert "InstanceTypeOfferings" in offerings
    offerings = offerings["InstanceTypeOfferings"]
    assert len(offerings) == 6
    for offrng in offerings:
        assert offrng["InstanceType"] == "t2.nano"
        assert offrng["LocationType"] == "availability-zone"
        assert offrng["Location"] in [
            "us-east-1a",
            "us-east-1b",
            "us-east-1c",
            "us-east-1d",
            "us-east-1e",
            "us-east-1f",
        ]


@mock_aws
def test_describe_instance_type_offering_filter_by_zone():
    client = boto3.client("ec2", "us-east-1")
    offerings = client.describe_instance_type_offerings(
        LocationType="availability-zone",
        Filters=[{"Name": "location", "Values": ["us-east-1c"]}],
    )

    assert "InstanceTypeOfferings" in offerings
    offerings = offerings["InstanceTypeOfferings"]
    # Exact number of offerings changes quite often, but it's a lot
    assert len(offerings) > 500
    assert all([o["LocationType"] == "availability-zone" for o in offerings])
    assert all([o["Location"] == "us-east-1c" for o in offerings])
    assert any([o["InstanceType"] == "a1.2xlarge" for o in offerings])


@mock_aws
def test_describe_instance_type_offering_filter_by_zone_id():
    client = boto3.client("ec2", "ca-central-1")
    offerings = client.describe_instance_type_offerings(
        LocationType="availability-zone-id",
        Filters=[
            {"Name": "location", "Values": ["cac1-az1"]},
            {"Name": "instance-type", "Values": ["c5.9xlarge"]},
        ],
    )

    assert "InstanceTypeOfferings" in offerings
    offerings = offerings["InstanceTypeOfferings"]
    assert len(offerings) == 1
    assert offerings[0]["LocationType"] == "availability-zone-id"
    assert offerings[0]["InstanceType"] == "c5.9xlarge"
    assert offerings[0]["Location"] == "cac1-az1"
