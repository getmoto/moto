from __future__ import unicode_literals
import boto
import boto3
import sure  # noqa
import pytest
from botocore.exceptions import ClientError

from moto import mock_ec2_deprecated, mock_ec2
from moto.ec2.models import OWNER_ID


@mock_ec2_deprecated
def test_default_network_acl_created_with_vpc():
    conn = boto.connect_vpc("the_key", "the secret")
    vpc = conn.create_vpc("10.0.0.0/16")
    all_network_acls = conn.get_all_network_acls()
    all_network_acls.should.have.length_of(2)


@mock_ec2_deprecated
def test_network_acls():
    conn = boto.connect_vpc("the_key", "the secret")
    vpc = conn.create_vpc("10.0.0.0/16")
    network_acl = conn.create_network_acl(vpc.id)
    all_network_acls = conn.get_all_network_acls()
    all_network_acls.should.have.length_of(3)


@mock_ec2_deprecated
def test_new_subnet_associates_with_default_network_acl():
    conn = boto.connect_vpc("the_key", "the secret")
    vpc = conn.get_all_vpcs()[0]

    subnet = conn.create_subnet(vpc.id, "172.31.112.0/20")
    all_network_acls = conn.get_all_network_acls()
    all_network_acls.should.have.length_of(1)

    acl = all_network_acls[0]
    acl.associations.should.have.length_of(7)
    [a.subnet_id for a in acl.associations].should.contain(subnet.id)


@mock_ec2_deprecated
def test_network_acl_entries():
    conn = boto.connect_vpc("the_key", "the secret")
    vpc = conn.create_vpc("10.0.0.0/16")

    network_acl = conn.create_network_acl(vpc.id)

    network_acl_entry = conn.create_network_acl_entry(
        network_acl.id,
        110,
        6,
        "ALLOW",
        "0.0.0.0/0",
        False,
        port_range_from="443",
        port_range_to="443",
    )

    all_network_acls = conn.get_all_network_acls()
    all_network_acls.should.have.length_of(3)

    test_network_acl = next(na for na in all_network_acls if na.id == network_acl.id)
    entries = test_network_acl.network_acl_entries
    entries.should.have.length_of(1)
    entries[0].rule_number.should.equal("110")
    entries[0].protocol.should.equal("6")
    entries[0].rule_action.should.equal("ALLOW")


@mock_ec2_deprecated
def test_delete_network_acl_entry():
    conn = boto.connect_vpc("the_key", "the secret")
    vpc = conn.create_vpc("10.0.0.0/16")

    network_acl = conn.create_network_acl(vpc.id)

    conn.create_network_acl_entry(
        network_acl.id,
        110,
        6,
        "ALLOW",
        "0.0.0.0/0",
        False,
        port_range_from="443",
        port_range_to="443",
    )
    conn.delete_network_acl_entry(network_acl.id, 110, False)

    all_network_acls = conn.get_all_network_acls()

    test_network_acl = next(na for na in all_network_acls if na.id == network_acl.id)
    entries = test_network_acl.network_acl_entries
    entries.should.have.length_of(0)


@mock_ec2_deprecated
def test_replace_network_acl_entry():
    conn = boto.connect_vpc("the_key", "the secret")
    vpc = conn.create_vpc("10.0.0.0/16")

    network_acl = conn.create_network_acl(vpc.id)

    conn.create_network_acl_entry(
        network_acl.id,
        110,
        6,
        "ALLOW",
        "0.0.0.0/0",
        False,
        port_range_from="443",
        port_range_to="443",
    )
    conn.replace_network_acl_entry(
        network_acl.id,
        110,
        -1,
        "DENY",
        "0.0.0.0/0",
        False,
        port_range_from="22",
        port_range_to="22",
    )

    all_network_acls = conn.get_all_network_acls()

    test_network_acl = next(na for na in all_network_acls if na.id == network_acl.id)
    entries = test_network_acl.network_acl_entries
    entries.should.have.length_of(1)
    entries[0].rule_number.should.equal("110")
    entries[0].protocol.should.equal("-1")
    entries[0].rule_action.should.equal("DENY")


@mock_ec2_deprecated
def test_associate_new_network_acl_with_subnet():
    conn = boto.connect_vpc("the_key", "the secret")
    vpc = conn.create_vpc("10.0.0.0/16")
    subnet = conn.create_subnet(vpc.id, "10.0.0.0/18")
    network_acl = conn.create_network_acl(vpc.id)

    conn.associate_network_acl(network_acl.id, subnet.id)

    all_network_acls = conn.get_all_network_acls()
    all_network_acls.should.have.length_of(3)

    test_network_acl = next(na for na in all_network_acls if na.id == network_acl.id)

    test_network_acl.associations.should.have.length_of(1)
    test_network_acl.associations[0].subnet_id.should.equal(subnet.id)


@mock_ec2_deprecated
def test_delete_network_acl():
    conn = boto.connect_vpc("the_key", "the secret")
    vpc = conn.create_vpc("10.0.0.0/16")
    subnet = conn.create_subnet(vpc.id, "10.0.0.0/18")
    network_acl = conn.create_network_acl(vpc.id)

    all_network_acls = conn.get_all_network_acls()
    all_network_acls.should.have.length_of(3)

    any(acl.id == network_acl.id for acl in all_network_acls).should.be.ok

    conn.delete_network_acl(network_acl.id)

    updated_network_acls = conn.get_all_network_acls()
    updated_network_acls.should.have.length_of(2)

    any(acl.id == network_acl.id for acl in updated_network_acls).shouldnt.be.ok


@mock_ec2_deprecated
def test_network_acl_tagging():
    conn = boto.connect_vpc("the_key", "the secret")
    vpc = conn.create_vpc("10.0.0.0/16")
    network_acl = conn.create_network_acl(vpc.id)

    network_acl.add_tag("a key", "some value")

    tag = conn.get_all_tags()[0]
    tag.name.should.equal("a key")
    tag.value.should.equal("some value")

    all_network_acls = conn.get_all_network_acls()
    test_network_acl = next(na for na in all_network_acls if na.id == network_acl.id)
    test_network_acl.tags.should.have.length_of(1)
    test_network_acl.tags["a key"].should.equal("some value")


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
    default_network_acl = next(iter(ec2.network_acls.all()), None)
    default_network_acl.is_default.should.be.ok

    default_network_acl.entries.should.have.length_of(4)
    unique_entries = []
    for entry in default_network_acl.entries:
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
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    default_network_acl = next(iter(ec2.network_acls.all()), None)
    default_network_acl.is_default.should.be.ok

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
    default_network_acl.is_default.should.be.ok

    rule_number = 200
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
    resp2.should.have.length_of(3)

    resp3 = conn.describe_network_acls(
        Filters=[{"Name": "owner-id", "Values": [OWNER_ID]}]
    )["NetworkAcls"]
    resp3.should.have.length_of(3)

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
