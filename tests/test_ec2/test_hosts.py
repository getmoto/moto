import boto3

from moto import mock_ec2
from uuid import uuid4


@mock_ec2
def test_allocate_hosts():
    client = boto3.client("ec2", "us-west-1")
    resp = client.allocate_hosts(
        AvailabilityZone="us-west-1a",
        InstanceType="a1.small",
        HostRecovery="off",
        AutoPlacement="on",
        Quantity=3,
    )
    assert len(resp["HostIds"]) == 3


@mock_ec2
def test_describe_hosts_with_instancefamily():
    client = boto3.client("ec2", "us-west-1")
    host_ids = client.allocate_hosts(
        AvailabilityZone="us-west-1a", InstanceFamily="c5", Quantity=1
    )["HostIds"]

    host = client.describe_hosts(HostIds=host_ids)["Hosts"][0]

    assert "AllocationTime" in host
    assert host["HostProperties"]["InstanceFamily"] == "c5"


@mock_ec2
def test_describe_hosts():
    client = boto3.client("ec2", "us-west-1")
    host_ids = client.allocate_hosts(
        AvailabilityZone="us-west-1c",
        InstanceType="a1.large",
        HostRecovery="on",
        AutoPlacement="off",
        Quantity=2,
    )["HostIds"]

    hosts = client.describe_hosts(HostIds=host_ids)["Hosts"]
    assert len(hosts) == 2

    assert hosts[0]["State"] == "available"
    assert hosts[0]["AvailabilityZone"] == "us-west-1c"
    assert hosts[0]["HostRecovery"] == "on"
    assert hosts[0]["HostProperties"]["InstanceType"] == "a1.large"
    assert hosts[0]["AutoPlacement"] == "off"


@mock_ec2
def test_describe_hosts_with_tags():
    client = boto3.client("ec2", "us-west-1")
    tagkey = str(uuid4())
    host_ids = client.allocate_hosts(
        AvailabilityZone="us-west-1b",
        InstanceType="b1.large",
        Quantity=1,
        TagSpecifications=[
            {"ResourceType": "dedicated-host", "Tags": [{"Key": tagkey, "Value": "v1"}]}
        ],
    )["HostIds"]

    host = client.describe_hosts(HostIds=host_ids)["Hosts"][0]
    assert host["Tags"] == [{"Key": tagkey, "Value": "v1"}]

    client.allocate_hosts(
        AvailabilityZone="us-west-1a", InstanceType="b1.large", Quantity=1
    )
    hosts = client.describe_hosts(Filters=[{"Name": "tag-key", "Values": [tagkey]}])[
        "Hosts"
    ]
    assert len(hosts) == 1


@mock_ec2
def test_describe_hosts_using_filters():
    client = boto3.client("ec2", "us-west-1")
    host_id1 = client.allocate_hosts(
        AvailabilityZone="us-west-1a", InstanceType="b1.large", Quantity=1
    )["HostIds"][0]
    host_id2 = client.allocate_hosts(
        AvailabilityZone="us-west-1b", InstanceType="b1.large", Quantity=1
    )["HostIds"][0]

    hosts = client.describe_hosts(
        Filters=[{"Name": "availability-zone", "Values": ["us-west-1b"]}]
    )["Hosts"]
    assert host_id2 in [h["HostId"] for h in hosts]

    hosts = client.describe_hosts(
        Filters=[{"Name": "availability-zone", "Values": ["us-west-1d"]}]
    )["Hosts"]
    assert len(hosts) == 0

    client.release_hosts(HostIds=[host_id1])
    hosts = client.describe_hosts(Filters=[{"Name": "state", "Values": ["released"]}])[
        "Hosts"
    ]
    assert host_id1 in [h["HostId"] for h in hosts]

    hosts = client.describe_hosts(
        Filters=[{"Name": "state", "Values": ["under-assessment"]}]
    )["Hosts"]
    assert len(hosts) == 0


@mock_ec2
def test_modify_hosts():
    client = boto3.client("ec2", "us-west-1")
    host_ids = client.allocate_hosts(
        AvailabilityZone="us-west-1a", InstanceFamily="c5", Quantity=1
    )["HostIds"]

    client.modify_hosts(
        HostIds=host_ids,
        AutoPlacement="off",
        HostRecovery="on",
        InstanceType="c5.medium",
    )

    host = client.describe_hosts(HostIds=host_ids)["Hosts"][0]

    assert host["AutoPlacement"] == "off"
    assert host["HostRecovery"] == "on"
    assert "InstanceFamily" not in host["HostProperties"]
    assert host["HostProperties"]["InstanceType"] == "c5.medium"


@mock_ec2
def test_release_hosts():
    client = boto3.client("ec2", "us-west-1")
    host_ids = client.allocate_hosts(
        AvailabilityZone="us-west-1a",
        InstanceType="a1.small",
        HostRecovery="off",
        AutoPlacement="on",
        Quantity=2,
    )["HostIds"]

    resp = client.release_hosts(HostIds=[host_ids[0]])
    assert resp["Successful"] == [host_ids[0]]

    host = client.describe_hosts(HostIds=[host_ids[0]])["Hosts"][0]

    assert host["State"] == "released"


@mock_ec2
def test_add_tags_to_dedicated_hosts():
    client = boto3.client("ec2", "us-west-1")
    resp = client.allocate_hosts(
        AvailabilityZone="us-west-1a", InstanceType="a1.small", Quantity=1
    )
    host_id = resp["HostIds"][0]

    client.create_tags(Resources=[host_id], Tags=[{"Key": "k1", "Value": "v1"}])

    host = client.describe_hosts(HostIds=[host_id])["Hosts"][0]
    assert host["Tags"] == [{"Key": "k1", "Value": "v1"}]
