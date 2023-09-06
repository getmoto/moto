import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_ec2, settings
from moto.core import DEFAULT_ACCOUNT_ID as OWNER_ID
from random import randint
from unittest import SkipTest


@mock_ec2
def test_default_network_acl_created_with_vpc():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")

    all_network_acls = client.describe_network_acls()["NetworkAcls"]
    our_acl = [a for a in all_network_acls if a["VpcId"] == vpc.id]
    assert len(our_acl) == 1
    assert our_acl[0]["IsDefault"] is True


@mock_ec2
def test_network_create_and_list_acls():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    created_acl = ec2.create_network_acl(VpcId=vpc.id)

    all_network_acls = client.describe_network_acls()["NetworkAcls"]

    acl_found = [
        a for a in all_network_acls if a["NetworkAclId"] == created_acl.network_acl_id
    ][0]
    assert acl_found["VpcId"] == vpc.id
    assert acl_found["Tags"] == []
    assert acl_found["IsDefault"] is False


@mock_ec2
def test_new_subnet_associates_with_default_network_acl():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("ServerMode will have conflicting CidrBlocks")
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    default_vpc = client.describe_vpcs()["Vpcs"][0]

    subnet = ec2.create_subnet(VpcId=default_vpc["VpcId"], CidrBlock="172.31.112.0/20")
    all_network_acls = client.describe_network_acls()["NetworkAcls"]
    assert len(all_network_acls) == 1

    acl = all_network_acls[0]
    assert len(acl["Associations"]) == 7
    assert subnet.id in [a["SubnetId"] for a in acl["Associations"]]


@mock_ec2
def test_network_acl_entries():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")

    network_acl = ec2.create_network_acl(VpcId=vpc.id)

    client.create_network_acl_entry(
        NetworkAclId=network_acl.id,
        RuleNumber=110,
        Protocol="6",  # TCP
        RuleAction="ALLOW",
        CidrBlock="0.0.0.0/0",
        Egress=False,
        PortRange={"From": 443, "To": 443},
    )

    all_network_acls = client.describe_network_acls()["NetworkAcls"]

    test_network_acl = next(
        na for na in all_network_acls if na["NetworkAclId"] == network_acl.id
    )
    assert test_network_acl["IsDefault"] is False

    entries = test_network_acl["Entries"]
    assert len(entries) == 1
    assert entries[0]["RuleNumber"] == 110
    assert entries[0]["Protocol"] == "6"
    assert entries[0]["RuleAction"] == "ALLOW"
    assert entries[0]["Egress"] is False
    assert entries[0]["PortRange"] == {"To": 443, "From": 443}
    assert entries[0]["CidrBlock"] == "0.0.0.0/0"


@mock_ec2
def test_delete_network_acl_entry():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")

    network_acl = ec2.create_network_acl(VpcId=vpc.id)

    client.create_network_acl_entry(
        NetworkAclId=network_acl.id,
        RuleNumber=110,
        Protocol="6",  # TCP
        RuleAction="ALLOW",
        CidrBlock="0.0.0.0/0",
        Egress=False,
        PortRange={"From": 443, "To": 443},
    )
    client.delete_network_acl_entry(
        NetworkAclId=network_acl.id, RuleNumber=110, Egress=False
    )

    all_network_acls = client.describe_network_acls()["NetworkAcls"]

    test_network_acl = next(
        na for na in all_network_acls if na["NetworkAclId"] == network_acl.id
    )
    assert len(test_network_acl["Entries"]) == 0


@mock_ec2
def test_replace_network_acl_entry():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")

    network_acl = ec2.create_network_acl(VpcId=vpc.id)

    client.create_network_acl_entry(
        NetworkAclId=network_acl.id,
        RuleNumber=110,
        Protocol="6",  # TCP
        RuleAction="ALLOW",
        CidrBlock="0.0.0.0/0",
        Egress=False,
        PortRange={"From": 443, "To": 443},
    )
    client.replace_network_acl_entry(
        NetworkAclId=network_acl.id,
        RuleNumber=110,
        Protocol="-1",
        RuleAction="DENY",
        CidrBlock="0.0.0.0/0",
        Egress=False,
        PortRange={"From": 22, "To": 22},
    )

    all_network_acls = client.describe_network_acls()["NetworkAcls"]

    test_network_acl = next(
        na for na in all_network_acls if na["NetworkAclId"] == network_acl.id
    )
    entries = test_network_acl["Entries"]
    assert len(entries) == 1
    assert entries[0]["RuleNumber"] == 110
    assert entries[0]["Protocol"] == "-1"
    assert entries[0]["RuleAction"] == "DENY"
    assert entries[0]["PortRange"] == {"To": 22, "From": 22}


@mock_ec2
def test_delete_network_acl():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    network_acl = ec2.create_network_acl(VpcId=vpc.id)

    all_network_acls = client.describe_network_acls()["NetworkAcls"]

    assert (
        any(acl["NetworkAclId"] == network_acl.id for acl in all_network_acls)
        is not None
    )

    client.delete_network_acl(NetworkAclId=network_acl.id)

    updated_network_acls = client.describe_network_acls()["NetworkAcls"]

    assert not any(
        acl["NetworkAclId"] == network_acl.id for acl in updated_network_acls
    )


@mock_ec2
def test_network_acl_tagging():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    network_acl = ec2.create_network_acl(VpcId=vpc.id)

    network_acl.create_tags(Tags=[{"Key": "a key", "Value": "some value"}])

    tag = client.describe_tags(
        Filters=[{"Name": "resource-id", "Values": [network_acl.id]}]
    )["Tags"][0]
    assert tag["ResourceId"] == network_acl.id
    assert tag["Key"] == "a key"
    assert tag["Value"] == "some value"

    all_network_acls = client.describe_network_acls()["NetworkAcls"]
    test_network_acl = next(
        na for na in all_network_acls if na["NetworkAclId"] == network_acl.id
    )
    assert test_network_acl["Tags"] == [{"Value": "some value", "Key": "a key"}]


@mock_ec2
def test_new_subnet_in_new_vpc_associates_with_default_network_acl():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    new_vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    new_vpc.reload()

    subnet = ec2.create_subnet(VpcId=new_vpc.id, CidrBlock="10.0.0.0/24")
    subnet.reload()

    new_vpcs_default_network_acl = next(iter(new_vpc.network_acls.all()), None)
    new_vpcs_default_network_acl.reload()
    assert new_vpcs_default_network_acl.vpc_id == new_vpc.id
    assert len(new_vpcs_default_network_acl.associations) == 1
    assert new_vpcs_default_network_acl.associations[0]["SubnetId"] == subnet.id


@mock_ec2
def test_default_network_acl_default_entries():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")

    if not settings.TEST_SERVER_MODE:
        # Can't know whether the first ACL is the default in ServerMode
        default_network_acl = next(iter(ec2.network_acls.all()), None)
        assert default_network_acl.is_default is True
        assert len(default_network_acl.entries) == 4

    vpc = client.create_vpc(CidrBlock="10.0.0.0/16")
    vpc_id = vpc["Vpc"]["VpcId"]

    default_acls = client.describe_network_acls(
        Filters=[
            {"Name": "default", "Values": ["true"]},
            {"Name": "vpc-id", "Values": [vpc_id]},
        ]
    )["NetworkAcls"]
    default_acl = default_acls[0]

    unique_entries = []
    for entry in default_acl["Entries"]:
        assert entry["CidrBlock"] == "0.0.0.0/0"
        assert entry["Protocol"] == "-1"
        assert entry["RuleNumber"] in [100, 32767]
        assert entry["RuleAction"] in ["allow", "deny"]
        assert isinstance(entry["Egress"], bool)
        if entry["RuleAction"] == "allow":
            assert entry["RuleNumber"] == 100
        else:
            assert entry["RuleNumber"] == 32767
        if entry not in unique_entries:
            unique_entries.append(entry)

    assert len(unique_entries) == 4


@mock_ec2
def test_delete_default_network_acl_default_entry():
    if settings.TEST_SERVER_MODE:
        raise SkipTest(
            "Don't want to mess with default ACLs in ServerMode, as other tests may need them"
        )
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    default_network_acl = next(iter(ec2.network_acls.all()), None)
    assert default_network_acl.is_default is True

    assert len(default_network_acl.entries) == 4
    first_default_network_acl_entry = default_network_acl.entries[0]

    default_network_acl.delete_entry(
        Egress=first_default_network_acl_entry["Egress"],
        RuleNumber=first_default_network_acl_entry["RuleNumber"],
    )

    assert len(default_network_acl.entries) == 3


@mock_ec2
def test_duplicate_network_acl_entry():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    default_network_acl = next(iter(ec2.network_acls.all()), None)
    assert default_network_acl.is_default is True

    rule_number = randint(0, 9999)
    egress = True
    default_network_acl.create_entry(
        CidrBlock="0.0.0.0/0",
        Egress=egress,
        Protocol="-1",
        RuleAction="allow",
        RuleNumber=rule_number,
    )

    with pytest.raises(ClientError) as ex:
        default_network_acl.create_entry(
            CidrBlock="10.0.0.0/0",
            Egress=egress,
            Protocol="-1",
            RuleAction="deny",
            RuleNumber=rule_number,
        )
    assert (
        str(ex.value)
        == f"An error occurred (NetworkAclEntryAlreadyExists) when calling the CreateNetworkAclEntry operation: The network acl entry identified by {rule_number} already exists."
    )


@mock_ec2
def test_describe_network_acls():
    conn = boto3.client("ec2", region_name="us-west-2")

    vpc = conn.create_vpc(CidrBlock="10.0.0.0/16")
    vpc_id = vpc["Vpc"]["VpcId"]

    network_acl = conn.create_network_acl(VpcId=vpc_id)

    network_acl_id = network_acl["NetworkAcl"]["NetworkAclId"]

    resp = conn.describe_network_acls(NetworkAclIds=[network_acl_id])
    result = resp["NetworkAcls"]

    assert len(result) == 1
    assert result[0]["NetworkAclId"] == network_acl_id

    resp2 = conn.describe_network_acls()["NetworkAcls"]
    assert network_acl_id in [na["NetworkAclId"] for na in resp2]

    resp3 = conn.describe_network_acls(
        Filters=[{"Name": "owner-id", "Values": [OWNER_ID]}]
    )["NetworkAcls"]
    assert network_acl_id in [na["NetworkAclId"] for na in resp3]

    # Assertions for filters
    network_acl_id = conn.create_network_acl(VpcId=vpc_id)["NetworkAcl"]["NetworkAclId"]
    cidr_block = "0.0.0.0/24"
    protocol = "17"  # UDP
    rule_number = 420
    rule_action = "allow"
    conn.create_network_acl_entry(
        NetworkAclId=network_acl_id,
        CidrBlock=cidr_block,
        Protocol=protocol,
        RuleNumber=rule_number,
        RuleAction=rule_action,
        Egress=False,
    )

    # Ensure filtering by entry CIDR block
    resp4 = conn.describe_network_acls(
        Filters=[{"Name": "entry.cidr", "Values": [cidr_block]}]
    )
    assert len(resp4["NetworkAcls"]) == 1
    assert resp4["NetworkAcls"][0]["NetworkAclId"] == network_acl_id
    assert cidr_block in [
        entry["CidrBlock"] for entry in resp4["NetworkAcls"][0]["Entries"]
    ]

    # Ensure filtering by entry protocol
    resp4 = conn.describe_network_acls(
        Filters=[{"Name": "entry.protocol", "Values": [protocol]}]
    )
    assert len(resp4["NetworkAcls"]) == 1
    assert resp4["NetworkAcls"][0]["NetworkAclId"] == network_acl_id
    assert protocol in [
        entry["Protocol"] for entry in resp4["NetworkAcls"][0]["Entries"]
    ]

    # Ensure filtering by entry rule number
    resp4 = conn.describe_network_acls(
        Filters=[{"Name": "entry.rule-number", "Values": [str(rule_number)]}]
    )
    assert len(resp4["NetworkAcls"]) == 1
    assert resp4["NetworkAcls"][0]["NetworkAclId"] == network_acl_id
    assert rule_number in [
        entry["RuleNumber"] for entry in resp4["NetworkAcls"][0]["Entries"]
    ]

    resp4 = conn.describe_network_acls(
        Filters=[{"Name": "entry.rule-number", "Values": [str(rule_number + 1)]}]
    )
    assert len(resp4["NetworkAcls"]) == 0

    # Ensure filtering by egress flag
    resp4 = conn.describe_network_acls(
        Filters=[{"Name": "entry.egress", "Values": ["false"]}]
    )
    assert network_acl_id in [entry["NetworkAclId"] for entry in resp4["NetworkAcls"]]
    # the ACL with network_acl_id contains no entries with Egress=True
    resp4 = conn.describe_network_acls(
        Filters=[{"Name": "entry.egress", "Values": ["true"]}]
    )
    assert network_acl_id not in [
        entry["NetworkAclId"] for entry in resp4["NetworkAcls"]
    ]

    # Ensure filtering by rule action
    resp4 = conn.describe_network_acls(
        Filters=[
            {"Name": "entry.rule-action", "Values": [rule_action]},
            {"Name": "id", "Values": [network_acl_id]},
        ]
    )
    assert len(resp4["NetworkAcls"]) == 1
    assert resp4["NetworkAcls"][0]["NetworkAclId"] == network_acl_id
    assert rule_action in [
        entry["RuleAction"] for entry in resp4["NetworkAcls"][0]["Entries"]
    ]

    with pytest.raises(ClientError) as ex:
        conn.describe_network_acls(NetworkAclIds=["1"])

    assert (
        str(ex.value)
        == "An error occurred (InvalidRouteTableID.NotFound) when calling the DescribeNetworkAcls operation: The routeTable ID '1' does not exist"
    )


@mock_ec2
def test_create_network_acl_with_tags():
    conn = boto3.client("ec2", region_name="us-west-2")

    vpc = conn.create_vpc(CidrBlock="10.0.0.0/16")
    vpc_id = vpc["Vpc"]["VpcId"]

    network_acl = conn.create_network_acl(
        VpcId=vpc_id,
        TagSpecifications=[
            {
                "ResourceType": "network-acl",
                "Tags": [{"Key": "test", "Value": "TestTags"}],
            }
        ],
    )

    assert (len(network_acl.get("NetworkAcl").get("Tags"))) == 1
    assert network_acl.get("NetworkAcl").get("Tags") == [
        {"Key": "test", "Value": "TestTags"}
    ]
