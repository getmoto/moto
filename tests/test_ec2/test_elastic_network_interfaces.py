from __future__ import unicode_literals

import pytest
import random

import boto3
from botocore.exceptions import ClientError
import boto
import boto.ec2
from boto.exception import EC2ResponseError
import sure  # noqa

from moto import mock_ec2, mock_ec2_deprecated, settings
from tests.helpers import requires_boto_gte
from uuid import uuid4


# Has boto3 equivalent
@mock_ec2_deprecated
def test_elastic_network_interfaces():
    conn = boto.connect_vpc("the_key", "the_secret")
    vpc = conn.create_vpc("10.0.0.0/16")
    subnet = conn.create_subnet(vpc.id, "10.0.0.0/18")

    with pytest.raises(EC2ResponseError) as ex:
        eni = conn.create_network_interface(subnet.id, dry_run=True)
    ex.value.error_code.should.equal("DryRunOperation")
    ex.value.status.should.equal(412)
    ex.value.message.should.equal(
        "An error occurred (DryRunOperation) when calling the CreateNetworkInterface operation: Request would have succeeded, but DryRun flag is set"
    )

    conn.create_network_interface(subnet.id)

    all_enis = conn.get_all_network_interfaces()
    all_enis.should.have.length_of(1)
    eni = all_enis[0]
    eni.groups.should.have.length_of(0)
    eni.private_ip_addresses.should.have.length_of(1)
    eni.private_ip_addresses[0].private_ip_address.startswith("10.").should.be.true

    with pytest.raises(EC2ResponseError) as ex:
        conn.delete_network_interface(eni.id, dry_run=True)
    ex.value.error_code.should.equal("DryRunOperation")
    ex.value.status.should.equal(412)
    ex.value.message.should.equal(
        "An error occurred (DryRunOperation) when calling the DeleteNetworkInterface operation: Request would have succeeded, but DryRun flag is set"
    )

    conn.delete_network_interface(eni.id)

    all_enis = conn.get_all_network_interfaces()
    all_enis.should.have.length_of(0)

    with pytest.raises(EC2ResponseError) as cm:
        conn.delete_network_interface(eni.id)
    cm.value.error_code.should.equal("InvalidNetworkInterfaceID.NotFound")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none


@mock_ec2
def test_elastic_network_interfaces_boto3():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    client = boto3.client("ec2", "us-east-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock="10.0.0.0/18")

    with pytest.raises(ClientError) as ex:
        ec2.create_network_interface(SubnetId=subnet.id, DryRun=True)
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the CreateNetworkInterface operation: Request would have succeeded, but DryRun flag is set"
    )

    eni_id = ec2.create_network_interface(SubnetId=subnet.id).id

    my_enis = client.describe_network_interfaces(NetworkInterfaceIds=[eni_id])[
        "NetworkInterfaces"
    ]
    my_enis.should.have.length_of(1)
    eni = my_enis[0]
    eni["Groups"].should.have.length_of(0)
    eni["PrivateIpAddresses"].should.have.length_of(1)
    eni["PrivateIpAddresses"][0]["PrivateIpAddress"].startswith("10.").should.be.true

    with pytest.raises(ClientError) as ex:
        client.delete_network_interface(NetworkInterfaceId=eni_id, DryRun=True)
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the DeleteNetworkInterface operation: Request would have succeeded, but DryRun flag is set"
    )

    client.delete_network_interface(NetworkInterfaceId=eni_id)

    all_enis = client.describe_network_interfaces()["NetworkInterfaces"]
    [eni["NetworkInterfaceId"] for eni in all_enis].shouldnt.contain(eni_id)

    with pytest.raises(ClientError) as ex:
        client.describe_network_interfaces(NetworkInterfaceIds=[eni_id])
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal(
        "InvalidNetworkInterfaceID.NotFound"
    )

    with pytest.raises(ClientError) as ex:
        client.delete_network_interface(NetworkInterfaceId=eni_id)
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal(
        "InvalidNetworkInterfaceID.NotFound"
    )


# Has boto3 equivalent
@mock_ec2_deprecated
def test_elastic_network_interfaces_subnet_validation():
    conn = boto.connect_vpc("the_key", "the_secret")

    with pytest.raises(EC2ResponseError) as cm:
        conn.create_network_interface("subnet-abcd1234")
    cm.value.error_code.should.equal("InvalidSubnetID.NotFound")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none


@mock_ec2
def test_elastic_network_interfaces_subnet_validation_boto3():
    client = boto3.client("ec2", "us-east-1")

    with pytest.raises(ClientError) as ex:
        client.create_network_interface(SubnetId="subnet-abcd1234")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("InvalidSubnetID.NotFound")


# Has boto3 equivalent
@mock_ec2_deprecated
def test_elastic_network_interfaces_with_private_ip():
    conn = boto.connect_vpc("the_key", "the_secret")
    vpc = conn.create_vpc("10.0.0.0/16")
    subnet = conn.create_subnet(vpc.id, "10.0.0.0/18")
    private_ip = "54.0.0.1"
    eni = conn.create_network_interface(subnet.id, private_ip)

    all_enis = conn.get_all_network_interfaces()
    all_enis.should.have.length_of(1)

    eni = all_enis[0]
    eni.groups.should.have.length_of(0)

    eni.private_ip_addresses.should.have.length_of(1)
    eni.private_ip_addresses[0].private_ip_address.should.equal(private_ip)


@mock_ec2
def test_elastic_network_interfaces_with_private_ip_boto3():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    client = boto3.client("ec2", "us-east-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock="10.0.0.0/18")

    private_ip = "54.0.0.1"
    eni = ec2.create_network_interface(SubnetId=subnet.id, PrivateIpAddress=private_ip)

    all_enis = client.describe_network_interfaces()["NetworkInterfaces"]
    [eni["NetworkInterfaceId"] for eni in all_enis].should.contain(eni.id)

    my_enis = client.describe_network_interfaces(NetworkInterfaceIds=[eni.id])[
        "NetworkInterfaces"
    ]

    eni = my_enis[0]
    eni["Groups"].should.have.length_of(0)

    eni["PrivateIpAddresses"].should.have.length_of(1)
    eni["PrivateIpAddresses"][0]["PrivateIpAddress"].should.equal(private_ip)


# Has boto3 equivalent
@mock_ec2_deprecated
def test_elastic_network_interfaces_with_groups():
    conn = boto.connect_vpc("the_key", "the_secret")
    vpc = conn.create_vpc("10.0.0.0/16")
    subnet = conn.create_subnet(vpc.id, "10.0.0.0/18")
    security_group1 = conn.create_security_group(
        "test security group #1", "this is a test security group"
    )
    security_group2 = conn.create_security_group(
        "test security group #2", "this is a test security group"
    )
    conn.create_network_interface(
        subnet.id, groups=[security_group1.id, security_group2.id]
    )

    all_enis = conn.get_all_network_interfaces()
    all_enis.should.have.length_of(1)

    eni = all_enis[0]
    eni.groups.should.have.length_of(2)
    set([group.id for group in eni.groups]).should.equal(
        set([security_group1.id, security_group2.id])
    )


@mock_ec2
def test_elastic_network_interfaces_with_groups_boto3():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    client = boto3.client("ec2", "us-east-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock="10.0.0.0/18")

    sec_group1 = ec2.create_security_group(GroupName=str(uuid4()), Description="n/a")
    sec_group2 = ec2.create_security_group(GroupName=str(uuid4()), Description="n/a")
    my_eni = subnet.create_network_interface(Groups=[sec_group1.id, sec_group2.id])

    all_enis = client.describe_network_interfaces()["NetworkInterfaces"]
    [eni["NetworkInterfaceId"] for eni in all_enis].should.contain(my_eni.id)

    my_eni = [eni for eni in all_enis if eni["NetworkInterfaceId"] == my_eni.id][0]
    my_eni["Groups"].should.have.length_of(2)
    set([group["GroupId"] for group in my_eni["Groups"]]).should.equal(
        set([sec_group1.id, sec_group2.id])
    )


# Has boto3 equivalent
@requires_boto_gte("2.12.0")
@mock_ec2_deprecated
def test_elastic_network_interfaces_modify_attribute():
    conn = boto.connect_vpc("the_key", "the_secret")
    vpc = conn.create_vpc("10.0.0.0/16")
    subnet = conn.create_subnet(vpc.id, "10.0.0.0/18")
    security_group1 = conn.create_security_group(
        "test security group #1", "this is a test security group"
    )
    security_group2 = conn.create_security_group(
        "test security group #2", "this is a test security group"
    )
    conn.create_network_interface(subnet.id, groups=[security_group1.id])

    all_enis = conn.get_all_network_interfaces()
    all_enis.should.have.length_of(1)

    eni = all_enis[0]
    eni.groups.should.have.length_of(1)
    eni.groups[0].id.should.equal(security_group1.id)

    with pytest.raises(EC2ResponseError) as ex:
        conn.modify_network_interface_attribute(
            eni.id, "groupset", [security_group1.id, security_group2.id], dry_run=True
        )
    ex.value.error_code.should.equal("DryRunOperation")
    ex.value.status.should.equal(412)
    ex.value.message.should.equal(
        "An error occurred (DryRunOperation) when calling the ModifyNetworkInterface operation: Request would have succeeded, but DryRun flag is set"
    )

    conn.modify_network_interface_attribute(
        eni.id, "groupset", [security_group1.id, security_group2.id]
    )

    all_enis = conn.get_all_network_interfaces()
    all_enis.should.have.length_of(1)

    eni = all_enis[0]
    eni.groups.should.have.length_of(2)
    eni.groups[0].id.should.equal(security_group1.id)
    eni.groups[1].id.should.equal(security_group2.id)


@mock_ec2
def test_elastic_network_interfaces_modify_attribute_boto3():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    client = boto3.client("ec2", "us-east-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock="10.0.0.0/18")
    sec_group1 = ec2.create_security_group(GroupName=str(uuid4()), Description="n/a")
    sec_group2 = ec2.create_security_group(GroupName=str(uuid4()), Description="n/a")
    eni_id = subnet.create_network_interface(Groups=[sec_group1.id]).id

    my_eni = client.describe_network_interfaces(NetworkInterfaceIds=[eni_id])[
        "NetworkInterfaces"
    ][0]

    my_eni["Groups"].should.have.length_of(1)
    my_eni["Groups"][0]["GroupId"].should.equal(sec_group1.id)

    with pytest.raises(ClientError) as ex:
        client.modify_network_interface_attribute(
            NetworkInterfaceId=eni_id, Groups=[sec_group2.id], DryRun=True
        )
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the ModifyNetworkInterface operation: Request would have succeeded, but DryRun flag is set"
    )

    client.modify_network_interface_attribute(
        NetworkInterfaceId=eni_id, Groups=[sec_group2.id]
    )

    my_eni = client.describe_network_interfaces(NetworkInterfaceIds=[eni_id])[
        "NetworkInterfaces"
    ][0]
    my_eni["Groups"].should.have.length_of(1)
    my_eni["Groups"][0]["GroupId"].should.equal(sec_group2.id)


# Has boto3 equivalent
@mock_ec2_deprecated
def test_elastic_network_interfaces_filtering():
    conn = boto.connect_vpc("the_key", "the_secret")
    vpc = conn.create_vpc("10.0.0.0/16")
    subnet = conn.create_subnet(vpc.id, "10.0.0.0/18")

    security_group1 = conn.create_security_group(
        "test security group #1", "this is a test security group"
    )
    security_group2 = conn.create_security_group(
        "test security group #2", "this is a test security group"
    )

    eni1 = conn.create_network_interface(
        subnet.id, groups=[security_group1.id, security_group2.id]
    )
    eni2 = conn.create_network_interface(subnet.id, groups=[security_group1.id])
    eni3 = conn.create_network_interface(subnet.id, description="test description")

    all_enis = conn.get_all_network_interfaces()
    all_enis.should.have.length_of(3)

    # Filter by NetworkInterfaceId
    enis_by_id = conn.get_all_network_interfaces([eni1.id])
    enis_by_id.should.have.length_of(1)
    set([eni.id for eni in enis_by_id]).should.equal(set([eni1.id]))

    # Filter by ENI ID
    enis_by_id = conn.get_all_network_interfaces(
        filters={"network-interface-id": eni1.id}
    )
    enis_by_id.should.have.length_of(1)
    set([eni.id for eni in enis_by_id]).should.equal(set([eni1.id]))

    # Filter by Security Group
    enis_by_group = conn.get_all_network_interfaces(
        filters={"group-id": security_group1.id}
    )
    enis_by_group.should.have.length_of(2)
    set([eni.id for eni in enis_by_group]).should.equal(set([eni1.id, eni2.id]))

    # Filter by ENI ID and Security Group
    enis_by_group = conn.get_all_network_interfaces(
        filters={"network-interface-id": eni1.id, "group-id": security_group1.id}
    )
    enis_by_group.should.have.length_of(1)
    set([eni.id for eni in enis_by_group]).should.equal(set([eni1.id]))

    # Filter by Description
    enis_by_description = conn.get_all_network_interfaces(
        filters={"description": eni3.description}
    )
    enis_by_description.should.have.length_of(1)
    enis_by_description[0].description.should.equal(eni3.description)

    # Unsupported filter
    conn.get_all_network_interfaces.when.called_with(
        filters={"not-implemented-filter": "foobar"}
    ).should.throw(NotImplementedError)


@mock_ec2
def test_elastic_network_interfaces_filtering_boto3():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    client = boto3.client("ec2", "us-east-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock="10.0.0.0/18")

    sec_group1 = ec2.create_security_group(GroupName=str(uuid4()), Description="n/a")
    sec_group2 = ec2.create_security_group(GroupName=str(uuid4()), Description="n/a")

    eni1 = subnet.create_network_interface(Groups=[sec_group1.id, sec_group2.id])
    eni2 = subnet.create_network_interface(Groups=[sec_group1.id])
    eni3 = subnet.create_network_interface(Description=str(uuid4()))

    all_enis = client.describe_network_interfaces()["NetworkInterfaces"]
    [eni["NetworkInterfaceId"] for eni in all_enis].should.contain(eni1.id)
    [eni["NetworkInterfaceId"] for eni in all_enis].should.contain(eni2.id)
    [eni["NetworkInterfaceId"] for eni in all_enis].should.contain(eni3.id)

    # Filter by NetworkInterfaceId
    enis_by_id = client.describe_network_interfaces(NetworkInterfaceIds=[eni1.id])[
        "NetworkInterfaces"
    ]
    enis_by_id.should.have.length_of(1)
    set([eni["NetworkInterfaceId"] for eni in enis_by_id]).should.equal(set([eni1.id]))

    # Filter by ENI ID
    enis_by_id = client.describe_network_interfaces(
        Filters=[{"Name": "network-interface-id", "Values": [eni1.id]}]
    )["NetworkInterfaces"]
    enis_by_id.should.have.length_of(1)
    set([eni["NetworkInterfaceId"] for eni in enis_by_id]).should.equal(set([eni1.id]))

    # Filter by Security Group
    enis_by_group = client.describe_network_interfaces(
        Filters=[{"Name": "group-id", "Values": [sec_group1.id]}]
    )["NetworkInterfaces"]
    enis_by_group.should.have.length_of(2)
    set([eni["NetworkInterfaceId"] for eni in enis_by_group]).should.equal(
        set([eni1.id, eni2.id])
    )

    # Filter by ENI ID and Security Group
    enis_by_group = client.describe_network_interfaces(
        Filters=[
            {"Name": "network-interface-id", "Values": [eni1.id]},
            {"Name": "group-id", "Values": [sec_group1.id]},
        ]
    )["NetworkInterfaces"]
    enis_by_group.should.have.length_of(1)
    set([eni["NetworkInterfaceId"] for eni in enis_by_group]).should.equal(
        set([eni1.id])
    )

    # Filter by Description
    enis_by_description = client.describe_network_interfaces(
        Filters=[{"Name": "description", "Values": [eni3.description]}]
    )["NetworkInterfaces"]
    enis_by_description.should.have.length_of(1)
    enis_by_description[0]["Description"].should.equal(eni3.description)

    # Unsupported filter
    if not settings.TEST_SERVER_MODE:
        # ServerMode will just throw a generic 500
        filters = [{"Name": "not-implemented-filter", "Values": ["foobar"]}]
        client.describe_network_interfaces.when.called_with(
            Filters=filters
        ).should.throw(NotImplementedError)


@mock_ec2
def test_elastic_network_interfaces_get_by_tag_name():
    ec2 = boto3.resource("ec2", region_name="us-west-2")
    ec2_client = boto3.client("ec2", region_name="us-west-2")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="10.0.0.0/24", AvailabilityZone="us-west-2a"
    )

    eni1 = ec2.create_network_interface(
        SubnetId=subnet.id, PrivateIpAddress="10.0.10.5"
    )

    with pytest.raises(ClientError) as ex:
        eni1.create_tags(Tags=[{"Key": "Name", "Value": "eni1"}], DryRun=True)
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the CreateTags operation: Request would have succeeded, but DryRun flag is set"
    )

    tag_value = str(uuid4())
    eni1.create_tags(Tags=[{"Key": "Name", "Value": tag_value}])

    # The status of the new interface should be 'available'
    waiter = ec2_client.get_waiter("network_interface_available")
    waiter.wait(NetworkInterfaceIds=[eni1.id])

    filters = [{"Name": "tag:Name", "Values": [tag_value]}]
    enis = list(ec2.network_interfaces.filter(Filters=filters))
    enis.should.have.length_of(1)

    filters = [{"Name": "tag:Name", "Values": ["wrong-name"]}]
    enis = list(ec2.network_interfaces.filter(Filters=filters))
    enis.should.have.length_of(0)


@mock_ec2
def test_elastic_network_interfaces_get_by_availability_zone():
    ec2 = boto3.resource("ec2", region_name="us-west-2")
    ec2_client = boto3.client("ec2", region_name="us-west-2")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet1 = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="10.0.0.0/24", AvailabilityZone="us-west-2a"
    )

    subnet2 = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="10.0.1.0/24", AvailabilityZone="us-west-2b"
    )

    eni1 = ec2.create_network_interface(
        SubnetId=subnet1.id, PrivateIpAddress="10.0.0.15"
    )

    eni2 = ec2.create_network_interface(
        SubnetId=subnet2.id, PrivateIpAddress="10.0.1.15"
    )

    # The status of the new interface should be 'available'
    waiter = ec2_client.get_waiter("network_interface_available")
    waiter.wait(NetworkInterfaceIds=[eni1.id, eni2.id])

    filters = [{"Name": "availability-zone", "Values": ["us-west-2a"]}]
    enis = list(ec2.network_interfaces.filter(Filters=filters))
    [eni.id for eni in enis].should.contain(eni1.id)
    [eni.id for eni in enis].shouldnt.contain(eni2.id)

    filters = [{"Name": "availability-zone", "Values": ["us-west-2c"]}]
    enis = list(ec2.network_interfaces.filter(Filters=filters))
    [eni.id for eni in enis].shouldnt.contain(eni1.id)
    [eni.id for eni in enis].shouldnt.contain(eni2.id)


@mock_ec2
def test_elastic_network_interfaces_get_by_private_ip():
    ec2 = boto3.resource("ec2", region_name="us-west-2")
    ec2_client = boto3.client("ec2", region_name="us-west-2")
    random_ip = ".".join(map(str, (random.randint(0, 99) for _ in range(4))))

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="10.0.0.0/24", AvailabilityZone="us-west-2a"
    )

    eni1 = ec2.create_network_interface(SubnetId=subnet.id, PrivateIpAddress=random_ip)

    # The status of the new interface should be 'available'
    waiter = ec2_client.get_waiter("network_interface_available")
    waiter.wait(NetworkInterfaceIds=[eni1.id])

    filters = [{"Name": "private-ip-address", "Values": [random_ip]}]
    enis = list(ec2.network_interfaces.filter(Filters=filters))
    enis.should.have.length_of(1)

    filters = [{"Name": "private-ip-address", "Values": ["10.0.10.10"]}]
    enis = list(ec2.network_interfaces.filter(Filters=filters))
    enis.should.have.length_of(0)

    filters = [{"Name": "addresses.private-ip-address", "Values": [random_ip]}]
    enis = list(ec2.network_interfaces.filter(Filters=filters))
    enis.should.have.length_of(1)

    filters = [{"Name": "addresses.private-ip-address", "Values": ["10.0.10.10"]}]
    enis = list(ec2.network_interfaces.filter(Filters=filters))
    enis.should.have.length_of(0)


@mock_ec2
def test_elastic_network_interfaces_get_by_vpc_id():
    ec2 = boto3.resource("ec2", region_name="us-west-2")
    ec2_client = boto3.client("ec2", region_name="us-west-2")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="10.0.0.0/24", AvailabilityZone="us-west-2a"
    )

    eni1 = ec2.create_network_interface(
        SubnetId=subnet.id, PrivateIpAddress="10.0.10.5"
    )

    # The status of the new interface should be 'available'
    waiter = ec2_client.get_waiter("network_interface_available")
    waiter.wait(NetworkInterfaceIds=[eni1.id])

    filters = [{"Name": "vpc-id", "Values": [subnet.vpc_id]}]
    enis = list(ec2.network_interfaces.filter(Filters=filters))
    enis.should.have.length_of(1)

    filters = [{"Name": "vpc-id", "Values": ["vpc-aaaa1111"]}]
    enis = list(ec2.network_interfaces.filter(Filters=filters))
    enis.should.have.length_of(0)


@mock_ec2
def test_elastic_network_interfaces_get_by_subnet_id():
    ec2 = boto3.resource("ec2", region_name="us-west-2")
    ec2_client = boto3.client("ec2", region_name="us-west-2")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="10.0.0.0/24", AvailabilityZone="us-west-2a"
    )

    eni1 = ec2.create_network_interface(
        SubnetId=subnet.id, PrivateIpAddress="10.0.10.5"
    )

    # The status of the new interface should be 'available'
    waiter = ec2_client.get_waiter("network_interface_available")
    waiter.wait(NetworkInterfaceIds=[eni1.id])

    filters = [{"Name": "subnet-id", "Values": [subnet.id]}]
    enis = list(ec2.network_interfaces.filter(Filters=filters))
    enis.should.have.length_of(1)

    filters = [{"Name": "subnet-id", "Values": ["subnet-aaaa1111"]}]
    enis = list(ec2.network_interfaces.filter(Filters=filters))
    enis.should.have.length_of(0)


@mock_ec2
def test_elastic_network_interfaces_get_by_description():
    ec2 = boto3.resource("ec2", region_name="us-west-2")
    ec2_client = boto3.client("ec2", region_name="us-west-2")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="10.0.0.0/24", AvailabilityZone="us-west-2a"
    )

    desc = str(uuid4())
    eni1 = ec2.create_network_interface(
        SubnetId=subnet.id, PrivateIpAddress="10.0.10.5", Description=desc
    )

    # The status of the new interface should be 'available'
    waiter = ec2_client.get_waiter("network_interface_available")
    waiter.wait(NetworkInterfaceIds=[eni1.id])

    filters = [{"Name": "description", "Values": [eni1.description]}]
    enis = list(ec2.network_interfaces.filter(Filters=filters))
    enis.should.have.length_of(1)

    filters = [{"Name": "description", "Values": ["bad description"]}]
    enis = list(ec2.network_interfaces.filter(Filters=filters))
    enis.should.have.length_of(0)


@mock_ec2
def test_elastic_network_interfaces_describe_network_interfaces_with_filter():
    ec2 = boto3.resource("ec2", region_name="us-west-2")
    ec2_client = boto3.client("ec2", region_name="us-west-2")

    random_ip = ".".join(map(str, (random.randint(0, 99) for _ in range(4))))

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="10.0.0.0/24", AvailabilityZone="us-west-2a"
    )

    sg = ec2_client.create_security_group(Description="test", GroupName=str(uuid4()))
    sg_id = sg["GroupId"]

    eni1 = ec2.create_network_interface(
        SubnetId=subnet.id,
        PrivateIpAddress=random_ip,
        Description=str(uuid4()),
        Groups=[sg_id],
    )

    # The status of the new interface should be 'available'
    waiter = ec2_client.get_waiter("network_interface_available")
    waiter.wait(NetworkInterfaceIds=[eni1.id])

    # Filter by network-interface-id
    response = ec2_client.describe_network_interfaces(
        Filters=[{"Name": "network-interface-id", "Values": [eni1.id]}]
    )
    response["NetworkInterfaces"].should.have.length_of(1)
    response["NetworkInterfaces"][0]["NetworkInterfaceId"].should.equal(eni1.id)
    response["NetworkInterfaces"][0]["PrivateIpAddress"].should.equal(
        eni1.private_ip_address
    )
    response["NetworkInterfaces"][0]["Description"].should.equal(eni1.description)

    # Filter by network-interface-id
    response = ec2_client.describe_network_interfaces(
        Filters=[{"Name": "group-id", "Values": [sg_id]}]
    )
    response["NetworkInterfaces"].should.have.length_of(1)
    response["NetworkInterfaces"][0]["NetworkInterfaceId"].should.equal(eni1.id)

    response = ec2_client.describe_network_interfaces(
        Filters=[{"Name": "network-interface-id", "Values": ["bad-id"]}]
    )
    response["NetworkInterfaces"].should.have.length_of(0)

    # Filter by private-ip-address
    response = ec2_client.describe_network_interfaces(
        Filters=[{"Name": "private-ip-address", "Values": [eni1.private_ip_address]}]
    )
    response["NetworkInterfaces"].should.have.length_of(1)
    response["NetworkInterfaces"][0]["NetworkInterfaceId"].should.equal(eni1.id)
    response["NetworkInterfaces"][0]["PrivateIpAddress"].should.equal(
        eni1.private_ip_address
    )
    response["NetworkInterfaces"][0]["Description"].should.equal(eni1.description)

    response = ec2_client.describe_network_interfaces(
        Filters=[{"Name": "private-ip-address", "Values": ["11.11.11.11"]}]
    )
    response["NetworkInterfaces"].should.have.length_of(0)

    # Filter by sunet-id
    response = ec2_client.describe_network_interfaces(
        Filters=[{"Name": "subnet-id", "Values": [eni1.subnet.id]}]
    )
    response["NetworkInterfaces"].should.have.length_of(1)
    response["NetworkInterfaces"][0]["NetworkInterfaceId"].should.equal(eni1.id)
    response["NetworkInterfaces"][0]["PrivateIpAddress"].should.equal(
        eni1.private_ip_address
    )
    response["NetworkInterfaces"][0]["Description"].should.equal(eni1.description)

    response = ec2_client.describe_network_interfaces(
        Filters=[{"Name": "subnet-id", "Values": ["sn-bad-id"]}]
    )
    response["NetworkInterfaces"].should.have.length_of(0)

    # Filter by description
    response = ec2_client.describe_network_interfaces(
        Filters=[{"Name": "description", "Values": [eni1.description]}]
    )
    response["NetworkInterfaces"].should.have.length_of(1)
    response["NetworkInterfaces"][0]["NetworkInterfaceId"].should.equal(eni1.id)
    response["NetworkInterfaces"][0]["PrivateIpAddress"].should.equal(
        eni1.private_ip_address
    )
    response["NetworkInterfaces"][0]["Description"].should.equal(eni1.description)

    response = ec2_client.describe_network_interfaces(
        Filters=[{"Name": "description", "Values": ["bad description"]}]
    )
    response["NetworkInterfaces"].should.have.length_of(0)

    # Filter by multiple filters
    response = ec2_client.describe_network_interfaces(
        Filters=[
            {"Name": "private-ip-address", "Values": [eni1.private_ip_address]},
            {"Name": "network-interface-id", "Values": [eni1.id]},
            {"Name": "subnet-id", "Values": [eni1.subnet.id]},
        ]
    )
    response["NetworkInterfaces"].should.have.length_of(1)
    response["NetworkInterfaces"][0]["NetworkInterfaceId"].should.equal(eni1.id)
    response["NetworkInterfaces"][0]["PrivateIpAddress"].should.equal(
        eni1.private_ip_address
    )
    response["NetworkInterfaces"][0]["Description"].should.equal(eni1.description)


@mock_ec2
def test_elastic_network_interfaces_filter_by_tag():
    ec2 = boto3.resource("ec2", region_name="us-west-2")
    ec2_client = boto3.client("ec2", region_name="us-west-2")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="10.0.0.0/24", AvailabilityZone="us-west-2a"
    )

    dev_env = f"dev-{str(uuid4())[0:4]}"
    prod_env = f"prod-{str(uuid4())[0:4]}"

    eni_dev = ec2.create_network_interface(
        SubnetId=subnet.id,
        PrivateIpAddress="10.0.10.5",
        Description="dev interface",
        TagSpecifications=[
            {
                "ResourceType": "network-interface",
                "Tags": [{"Key": "environment", "Value": dev_env}],
            },
        ],
    )

    eni_prod = ec2.create_network_interface(
        SubnetId=subnet.id,
        PrivateIpAddress="10.0.10.6",
        Description="prod interface",
        TagSpecifications=[
            {
                "ResourceType": "network-interface",
                "Tags": [{"Key": "environment", "Value": prod_env}],
            },
        ],
    )

    for eni in [eni_dev, eni_prod]:
        waiter = ec2_client.get_waiter("network_interface_available")
        waiter.wait(NetworkInterfaceIds=[eni.id])

    resp = ec2_client.describe_network_interfaces(
        Filters=[{"Name": "tag:environment", "Values": ["staging"]}]
    )
    resp["NetworkInterfaces"].should.have.length_of(0)

    resp = ec2_client.describe_network_interfaces(
        Filters=[{"Name": "tag:environment", "Values": [dev_env]}]
    )
    resp["NetworkInterfaces"].should.have.length_of(1)
    resp["NetworkInterfaces"][0]["Description"].should.equal("dev interface")

    resp = ec2_client.describe_network_interfaces(
        Filters=[{"Name": "tag:environment", "Values": [prod_env]}]
    )
    resp["NetworkInterfaces"].should.have.length_of(1)
    resp["NetworkInterfaces"][0]["Description"].should.equal("prod interface")

    resp = ec2_client.describe_network_interfaces(
        Filters=[{"Name": "tag:environment", "Values": [dev_env, prod_env]}]
    )
    resp["NetworkInterfaces"].should.have.length_of(2)


@mock_ec2
def test_elastic_network_interfaces_auto_create_securitygroup():
    ec2 = boto3.resource("ec2", region_name="us-west-2")
    ec2_client = boto3.client("ec2", region_name="us-west-2")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="10.0.0.0/24", AvailabilityZone="us-west-2a"
    )

    eni1 = ec2.create_network_interface(
        SubnetId=subnet.id, PrivateIpAddress="10.0.10.5", Groups=["testgroup"]
    )

    # The status of the new interface should be 'available'
    waiter = ec2_client.get_waiter("network_interface_available")
    waiter.wait(NetworkInterfaceIds=[eni1.id])

    sgs = ec2_client.describe_security_groups()["SecurityGroups"]
    found_sg = [sg for sg in sgs if sg["GroupId"] == "testgroup"]
    found_sg.should.have.length_of(1)

    found_sg[0]["GroupName"].should.equal("testgroup")
    found_sg[0]["Description"].should.equal("testgroup")
