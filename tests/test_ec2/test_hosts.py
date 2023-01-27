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
    resp["HostIds"].should.have.length_of(3)


@mock_ec2
def test_describe_hosts_with_instancefamily():
    client = boto3.client("ec2", "us-west-1")
    host_ids = client.allocate_hosts(
        AvailabilityZone="us-west-1a", InstanceFamily="c5", Quantity=1
    )["HostIds"]

    host = client.describe_hosts(HostIds=host_ids)["Hosts"][0]

    host.should.have.key("HostProperties").should.have.key("InstanceFamily").equals(
        "c5"
    )


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
    hosts.should.have.length_of(2)

    hosts[0].should.have.key("State").equals("available")
    hosts[0].should.have.key("AvailabilityZone").equals("us-west-1c")
    hosts[0].should.have.key("HostRecovery").equals("on")
    hosts[0].should.have.key("HostProperties").should.have.key("InstanceType").equals(
        "a1.large"
    )
    hosts[0].should.have.key("AutoPlacement").equals("off")


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
    host.should.have.key("Tags").equals([{"Key": tagkey, "Value": "v1"}])

    client.allocate_hosts(
        AvailabilityZone="us-west-1a", InstanceType="b1.large", Quantity=1
    )
    hosts = client.describe_hosts(Filters=[{"Name": "tag-key", "Values": [tagkey]}])[
        "Hosts"
    ]
    hosts.should.have.length_of(1)


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
    [h["HostId"] for h in hosts].should.contain(host_id2)

    hosts = client.describe_hosts(
        Filters=[{"Name": "availability-zone", "Values": ["us-west-1d"]}]
    )["Hosts"]
    hosts.should.have.length_of(0)

    client.release_hosts(HostIds=[host_id1])
    hosts = client.describe_hosts(Filters=[{"Name": "state", "Values": ["released"]}])[
        "Hosts"
    ]
    [h["HostId"] for h in hosts].should.contain(host_id1)

    hosts = client.describe_hosts(
        Filters=[{"Name": "state", "Values": ["under-assessment"]}]
    )["Hosts"]
    hosts.should.have.length_of(0)


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

    host.should.have.key("AutoPlacement").equals("off")
    host.should.have.key("HostRecovery").equals("on")
    host.should.have.key("HostProperties").shouldnt.have.key("InstanceFamily")
    host.should.have.key("HostProperties").should.have.key("InstanceType").equals(
        "c5.medium"
    )


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
    resp.should.have.key("Successful").equals([host_ids[0]])

    host = client.describe_hosts(HostIds=[host_ids[0]])["Hosts"][0]

    host.should.have.key("State").equals("released")


@mock_ec2
def test_add_tags_to_dedicated_hosts():
    client = boto3.client("ec2", "us-west-1")
    resp = client.allocate_hosts(
        AvailabilityZone="us-west-1a", InstanceType="a1.small", Quantity=1
    )
    host_id = resp["HostIds"][0]

    client.create_tags(Resources=[host_id], Tags=[{"Key": "k1", "Value": "v1"}])

    host = client.describe_hosts(HostIds=[host_id])["Hosts"][0]
    host.should.have.key("Tags").equals([{"Key": "k1", "Value": "v1"}])
