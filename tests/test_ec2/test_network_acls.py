import boto3
import sure  # noqa # pylint: disable=unused-import
import pytest
from botocore.exceptions import ClientError

from moto import mock_ec2, settings
from moto.ec2.models import OWNER_ID
from random import randint
from unittest import SkipTest


@mock_ec2
def test_default_network_acl_created_with_vpc():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")

    all_network_acls = client.describe_network_acls()["NetworkAcls"]
    our_acl = [a for a in all_network_acls if a["VpcId"] == vpc.id]
    our_acl.should.have.length_of(1)
    our_acl[0].should.have.key("IsDefault").equals(True)


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
    acl_found["VpcId"].should.equal(vpc.id)
    acl_found["Tags"].should.equal([])
    acl_found["IsDefault"].should.equal(False)


@mock_ec2
def test_new_subnet_associates_with_default_network_acl():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("ServerMode will have conflicting CidrBlocks")
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    default_vpc = client.describe_vpcs()["Vpcs"][0]

    subnet = ec2.create_subnet(VpcId=default_vpc["VpcId"], CidrBlock="172.31.112.0/20")
    all_network_acls = client.describe_network_acls()["NetworkAcls"]
    all_network_acls.should.have.length_of(1)

    acl = all_network_acls[0]
    acl["Associations"].should.have.length_of(7)
    [a["SubnetId"] for a in acl["Associations"]].should.contain(subnet.id)


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
    test_network_acl.should.have.key("IsDefault").should.equal(False)

    entries = test_network_acl["Entries"]
    entries.should.have.length_of(1)
    entries[0]["RuleNumber"].should.equal(110)
    entries[0]["Protocol"].should.equal("6")
    entries[0]["RuleAction"].should.equal("ALLOW")
    entries[0]["Egress"].should.equal(False)
    entries[0]["PortRange"].should.equal({"To": 443, "From": 443})
    entries[0]["CidrBlock"].should.equal("0.0.0.0/0")


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
    test_network_acl["Entries"].should.have.length_of(0)


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
    entries.should.have.length_of(1)
    entries[0]["RuleNumber"].should.equal(110)
    entries[0]["Protocol"].should.equal("-1")
    entries[0]["RuleAction"].should.equal("DENY")
    entries[0]["PortRange"].should.equal({"To": 22, "From": 22})


@mock_ec2
def test_delete_network_acl():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    network_acl = ec2.create_network_acl(VpcId=vpc.id)

    all_network_acls = client.describe_network_acls()["NetworkAcls"]

    any(acl["NetworkAclId"] == network_acl.id for acl in all_network_acls).should.be.ok

    client.delete_network_acl(NetworkAclId=network_acl.id)

    updated_network_acls = client.describe_network_acls()["NetworkAcls"]

    any(
        acl["NetworkAclId"] == network_acl.id for acl in updated_network_acls
    ).shouldnt.be.ok


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
    tag.should.have.key("ResourceId").equal(network_acl.id)
    tag.should.have.key("Key").equal("a key")
    tag.should.have.key("Value").equal("some value")

    all_network_acls = client.describe_network_acls()["NetworkAcls"]
    test_network_acl = next(
        na for na in all_network_acls if na["NetworkAclId"] == network_acl.id
    )
    test_network_acl["Tags"].should.equal([{"Value": "some value", "Key": "a key"}])


@mock_ec2
def test_new_subnet_in_new_vpc_associates_with_default_network_acl():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    new_vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    new_vpc.reload()

    subnet = ec2.create_subnet(VpcId=new_vpc.id, CidrBlock="10.0.0.0/24")
    subnet.reload()

    new_vpcs_default_network_acl = next(iter(new_vpc.network_acls.all()), None)
    new_vpcs_default_network_acl.reload()
    new_vpcs_default_network_acl.vpc_id.should.equal(new_vpc.id)
    new_vpcs_default_network_acl.associations.should.have.length_of(1)
    new_vpcs_default_network_acl.associations[0]["SubnetId"].should.equal(subnet.id)


@mock_ec2
def test_default_network_acl_default_entries():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")

    if not settings.TEST_SERVER_MODE:
        # Can't know whether the first ACL is the default in ServerMode
        default_network_acl = next(iter(ec2.network_acls.all()), None)
        default_network_acl.is_default.should.equal(True)
        default_network_acl.entries.should.have.length_of(4)

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
        entry["CidrBlock"].should.equal("0.0.0.0/0")
        entry["Protocol"].should.equal("-1")
        entry["RuleNumber"].should.be.within([100, 32767])
        entry["RuleAction"].should.be.within(["allow", "deny"])
        assert type(entry["Egress"]) is bool
        if entry["RuleAction"] == "allow":
            entry["RuleNumber"].should.be.equal(100)
        else:
            entry["RuleNumber"].should.be.equal(32767)
        if entry not in unique_entries:
            unique_entries.append(entry)

    unique_entries.should.have.length_of(4)


@mock_ec2
def test_delete_default_network_acl_default_entry():
    if settings.TEST_SERVER_MODE:
        raise SkipTest(
            "Don't want to mess with default ACLs in ServerMode, as other tests may need them"
        )
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    default_network_acl = next(iter(ec2.network_acls.all()), None)
    default_network_acl.is_default.should.equal(True)

    default_network_acl.entries.should.have.length_of(4)
    first_default_network_acl_entry = default_network_acl.entries[0]

    default_network_acl.delete_entry(
        Egress=first_default_network_acl_entry["Egress"],
        RuleNumber=first_default_network_acl_entry["RuleNumber"],
    )

    default_network_acl.entries.should.have.length_of(3)


@mock_ec2
def test_duplicate_network_acl_entry():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    default_network_acl = next(iter(ec2.network_acls.all()), None)
    default_network_acl.is_default.should.equal(True)

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
    str(ex.value).should.equal(
        "An error occurred (NetworkAclEntryAlreadyExists) when calling the CreateNetworkAclEntry "
        "operation: The network acl entry identified by {} already exists.".format(
            rule_number
        )
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

    result.should.have.length_of(1)
    result[0]["NetworkAclId"].should.equal(network_acl_id)

    resp2 = conn.describe_network_acls()["NetworkAcls"]
    [na["NetworkAclId"] for na in resp2].should.contain(network_acl_id)

    resp3 = conn.describe_network_acls(
        Filters=[{"Name": "owner-id", "Values": [OWNER_ID]}]
    )["NetworkAcls"]
    [na["NetworkAclId"] for na in resp3].should.contain(network_acl_id)

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
    resp4["NetworkAcls"].should.have.length_of(1)
    resp4["NetworkAcls"][0]["NetworkAclId"].should.equal(network_acl_id)
    [entry["CidrBlock"] for entry in resp4["NetworkAcls"][0]["Entries"]].should.contain(
        cidr_block
    )

    # Ensure filtering by entry protocol
    resp4 = conn.describe_network_acls(
        Filters=[{"Name": "entry.protocol", "Values": [protocol]}]
    )
    resp4["NetworkAcls"].should.have.length_of(1)
    resp4["NetworkAcls"][0]["NetworkAclId"].should.equal(network_acl_id)
    [entry["Protocol"] for entry in resp4["NetworkAcls"][0]["Entries"]].should.contain(
        protocol
    )

    # Ensure filtering by entry rule number
    resp4 = conn.describe_network_acls(
        Filters=[{"Name": "entry.rule-number", "Values": [str(rule_number)]}]
    )
    resp4["NetworkAcls"].should.have.length_of(1)
    resp4["NetworkAcls"][0]["NetworkAclId"].should.equal(network_acl_id)
    [
        entry["RuleNumber"] for entry in resp4["NetworkAcls"][0]["Entries"]
    ].should.contain(rule_number)

    resp4 = conn.describe_network_acls(
        Filters=[{"Name": "entry.rule-number", "Values": [str(rule_number + 1)]}]
    )
    resp4["NetworkAcls"].should.have.length_of(0)

    # Ensure filtering by egress flag
    resp4 = conn.describe_network_acls(
        Filters=[{"Name": "entry.egress", "Values": ["false"]}]
    )
    [entry["NetworkAclId"] for entry in resp4["NetworkAcls"]].should.contain(
        network_acl_id
    )
    # the ACL with network_acl_id contains no entries with Egress=True
    resp4 = conn.describe_network_acls(
        Filters=[{"Name": "entry.egress", "Values": ["true"]}]
    )
    [entry["NetworkAclId"] for entry in resp4["NetworkAcls"]].shouldnt.contain(
        network_acl_id
    )

    # Ensure filtering by rule action
    resp4 = conn.describe_network_acls(
        Filters=[
            {"Name": "entry.rule-action", "Values": [rule_action]},
            {"Name": "id", "Values": [network_acl_id]},
        ]
    )
    resp4["NetworkAcls"].should.have.length_of(1)
    resp4["NetworkAcls"][0]["NetworkAclId"].should.equal(network_acl_id)
    [
        entry["RuleAction"] for entry in resp4["NetworkAcls"][0]["Entries"]
    ].should.contain(rule_action)

    with pytest.raises(ClientError) as ex:
        conn.describe_network_acls(NetworkAclIds=["1"])

    str(ex.value).should.equal(
        "An error occurred (InvalidRouteTableID.NotFound) when calling the "
        "DescribeNetworkAcls operation: The routeTable ID '1' does not exist"
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

    (len(network_acl.get("NetworkAcl").get("Tags"))).should.equal(1)
    network_acl.get("NetworkAcl").get("Tags").should.equal(
        [{"Key": "test", "Value": "TestTags"}]
    )
