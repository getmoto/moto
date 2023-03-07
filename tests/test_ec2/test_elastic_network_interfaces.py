import pytest
import random

import boto3
from botocore.exceptions import ClientError
import sure  # noqa # pylint: disable=unused-import

from moto import mock_ec2, settings
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from moto.ec2.utils import random_private_ip
from tests import EXAMPLE_AMI_ID
from uuid import uuid4


@mock_ec2
def test_elastic_network_interfaces():
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
    eni["Groups"].should.have.length_of(1)
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


@mock_ec2
def test_elastic_network_interfaces_subnet_validation():
    client = boto3.client("ec2", "us-east-1")

    with pytest.raises(ClientError) as ex:
        client.create_network_interface(SubnetId="subnet-abcd1234")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("InvalidSubnetID.NotFound")


@mock_ec2
def test_elastic_network_interfaces_with_private_ip():
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
    eni["Groups"].should.have.length_of(1)

    eni["PrivateIpAddresses"].should.have.length_of(1)
    eni["PrivateIpAddresses"][0]["PrivateIpAddress"].should.equal(private_ip)


@mock_ec2
def test_elastic_network_interfaces_with_groups():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    client = boto3.client("ec2", "us-east-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock="10.0.0.0/18")

    sec_group1 = ec2.create_security_group(GroupName=str(uuid4()), Description="n/a")
    sec_group2 = ec2.create_security_group(GroupName=str(uuid4()), Description="n/a")
    my_eni = subnet.create_network_interface(Groups=[sec_group1.id, sec_group2.id])

    all_enis = client.describe_network_interfaces()["NetworkInterfaces"]
    [eni["NetworkInterfaceId"] for eni in all_enis].should.contain(my_eni.id)

    my_eni_description = [
        eni for eni in all_enis if eni["NetworkInterfaceId"] == my_eni.id
    ][0]
    my_eni_description["Groups"].should.have.length_of(2)
    set([group["GroupId"] for group in my_eni_description["Groups"]]).should.equal(
        set([sec_group1.id, sec_group2.id])
    )

    eni_groups_attribute = client.describe_network_interface_attribute(
        NetworkInterfaceId=my_eni.id, Attribute="groupSet"
    ).get("Groups")

    eni_groups_attribute.should.have.length_of(2)
    set([group["GroupId"] for group in eni_groups_attribute]).should.equal(
        set([sec_group1.id, sec_group2.id])
    )


@mock_ec2
def test_elastic_network_interfaces_without_group():
    # ENI should use the default SecurityGroup if not provided
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    client = boto3.client("ec2", "us-east-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock="10.0.0.0/18")

    my_eni = subnet.create_network_interface()

    all_enis = client.describe_network_interfaces()["NetworkInterfaces"]
    [eni["NetworkInterfaceId"] for eni in all_enis].should.contain(my_eni.id)

    my_eni = [eni for eni in all_enis if eni["NetworkInterfaceId"] == my_eni.id][0]
    my_eni["Groups"].should.have.length_of(1)
    my_eni["Groups"][0]["GroupName"].should.equal("default")


@mock_ec2
def test_elastic_network_interfaces_modify_attribute():
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
        "An error occurred (DryRunOperation) when calling the ModifyNetworkInterfaceAttribute operation: Request would have succeeded, but DryRun flag is set"
    )

    client.modify_network_interface_attribute(
        NetworkInterfaceId=eni_id, Groups=[sec_group2.id]
    )

    my_eni = client.describe_network_interfaces(NetworkInterfaceIds=[eni_id])[
        "NetworkInterfaces"
    ][0]
    my_eni["Groups"].should.have.length_of(1)
    my_eni["Groups"][0]["GroupId"].should.equal(sec_group2.id)


@mock_ec2
def test_elastic_network_interfaces_filtering():
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
def test_elastic_network_interfaces_get_by_attachment_instance_id():
    ec2_resource = boto3.resource("ec2", region_name="us-west-2")
    ec2_client = boto3.client("ec2", region_name="us-west-2")

    vpc = ec2_resource.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2_resource.create_subnet(
        VpcId=vpc.id, CidrBlock="10.0.0.0/24", AvailabilityZone="us-west-2a"
    )

    security_group1 = ec2_resource.create_security_group(
        GroupName=str(uuid4()), Description="desc"
    )

    create_instances_result = ec2_resource.create_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1
    )
    instance = create_instances_result[0]

    # we should have one ENI attached to our ec2 instance by default
    filters = [{"Name": "attachment.instance-id", "Values": [instance.id]}]
    enis = ec2_client.describe_network_interfaces(Filters=filters)
    enis.get("NetworkInterfaces").should.have.length_of(1)

    # attach another ENI to our existing instance, total should be 2
    eni1 = ec2_resource.create_network_interface(
        SubnetId=subnet.id, Groups=[security_group1.id]
    )
    ec2_client.attach_network_interface(
        NetworkInterfaceId=eni1.id, InstanceId=instance.id, DeviceIndex=1
    )

    filters = [{"Name": "attachment.instance-id", "Values": [instance.id]}]
    enis = ec2_client.describe_network_interfaces(Filters=filters)
    enis.get("NetworkInterfaces").should.have.length_of(2)

    # we shouldn't find any ENIs that are attached to this fake instance ID
    filters = [{"Name": "attachment.instance-id", "Values": ["this-doesnt-match-lol"]}]
    enis = ec2_client.describe_network_interfaces(Filters=filters)
    enis.get("NetworkInterfaces").should.have.length_of(0)


@mock_ec2
def test_elastic_network_interfaces_get_by_attachment_instance_owner_id():
    ec2_resource = boto3.resource("ec2", region_name="us-west-2")
    ec2_client = boto3.client("ec2", region_name="us-west-2")

    vpc = ec2_resource.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2_resource.create_subnet(
        VpcId=vpc.id, CidrBlock="10.0.0.0/24", AvailabilityZone="us-west-2a"
    )

    security_group1 = ec2_resource.create_security_group(
        GroupName=str(uuid4()), Description="desc"
    )

    create_instances_result = ec2_resource.create_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1
    )
    instance = create_instances_result[0]

    eni1 = ec2_resource.create_network_interface(
        SubnetId=subnet.id, Groups=[security_group1.id]
    )
    ec2_client.attach_network_interface(
        NetworkInterfaceId=eni1.id, InstanceId=instance.id, DeviceIndex=1
    )

    filters = [{"Name": "attachment.instance-owner-id", "Values": [ACCOUNT_ID]}]
    enis = ec2_client.describe_network_interfaces(Filters=filters)["NetworkInterfaces"]
    eni_ids = [eni["NetworkInterfaceId"] for eni in enis]
    eni_ids.should.contain(eni1.id)


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


@mock_ec2
def test_assign_private_ip_addresses():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    client = boto3.client("ec2", "us-east-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock="10.0.0.0/18")

    private_ip = "54.0.0.1"
    eni = ec2.create_network_interface(SubnetId=subnet.id, PrivateIpAddress=private_ip)

    resp = client.describe_network_interfaces(NetworkInterfaceIds=[eni.id])
    my_eni = resp["NetworkInterfaces"][0]
    my_eni.should.have.key("PrivateIpAddress").equals("54.0.0.1")
    my_eni.should.have.key("PrivateIpAddresses").equals(
        [{"Primary": True, "PrivateIpAddress": "54.0.0.1"}]
    )

    # Do not pass SecondaryPrivateIpAddressCount-parameter
    client.assign_private_ip_addresses(NetworkInterfaceId=eni.id)

    # Verify nothing changes
    resp = client.describe_network_interfaces(NetworkInterfaceIds=[eni.id])
    my_eni = resp["NetworkInterfaces"][0]
    my_eni.should.have.key("PrivateIpAddress").equals("54.0.0.1")
    my_eni.should.have.key("PrivateIpAddresses").equals(
        [{"Primary": True, "PrivateIpAddress": "54.0.0.1"}]
    )


@mock_ec2
def test_assign_private_ip_addresses__with_secondary_count():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    client = boto3.client("ec2", "us-east-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock="10.0.0.0/18")

    private_ip = "54.0.0.1"
    eni = ec2.create_network_interface(SubnetId=subnet.id, PrivateIpAddress=private_ip)

    client.assign_private_ip_addresses(
        NetworkInterfaceId=eni.id, SecondaryPrivateIpAddressCount=2
    )

    # Verify second ip's are added
    resp = client.describe_network_interfaces(NetworkInterfaceIds=[eni.id])
    my_eni = resp["NetworkInterfaces"][0]

    my_eni.should.have.key("PrivateIpAddress").equals("54.0.0.1")
    my_eni.should.have.key("PrivateIpAddresses").should.have.length_of(3)
    my_eni.should.have.key("PrivateIpAddresses").contain(
        {"Primary": True, "PrivateIpAddress": "54.0.0.1"}
    )

    # Not as ipv6 addresses though
    my_eni.should.have.key("Ipv6Addresses").equals([])


@mock_ec2
def test_unassign_private_ip_addresses():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    client = boto3.client("ec2", "us-east-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock="10.0.0.0/18")

    private_ip = "54.0.0.1"
    eni = ec2.create_network_interface(SubnetId=subnet.id, PrivateIpAddress=private_ip)

    client.assign_private_ip_addresses(
        NetworkInterfaceId=eni.id, SecondaryPrivateIpAddressCount=2
    )
    resp = client.describe_network_interfaces(NetworkInterfaceIds=[eni.id])
    my_eni = resp["NetworkInterfaces"][0]
    ips_before = [addr["PrivateIpAddress"] for addr in my_eni["PrivateIpAddresses"]]

    # Remove IP
    resp = client.unassign_private_ip_addresses(
        NetworkInterfaceId=eni.id, PrivateIpAddresses=[ips_before[1]]
    )

    # Verify it's gone
    resp = client.describe_network_interfaces(NetworkInterfaceIds=[eni.id])
    my_eni = resp["NetworkInterfaces"][0]
    my_eni.should.have.key("PrivateIpAddresses").should.have.length_of(2)
    my_eni.should.have.key("PrivateIpAddresses").contain(
        {"Primary": True, "PrivateIpAddress": "54.0.0.1"}
    )
    my_eni.should.have.key("PrivateIpAddresses").contain(
        {"Primary": False, "PrivateIpAddress": ips_before[2]}
    )


@mock_ec2
def test_unassign_private_ip_addresses__multiple():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    client = boto3.client("ec2", "us-east-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock="10.0.0.0/18")

    private_ip = "54.0.0.1"
    eni = ec2.create_network_interface(SubnetId=subnet.id, PrivateIpAddress=private_ip)

    client.assign_private_ip_addresses(
        NetworkInterfaceId=eni.id, SecondaryPrivateIpAddressCount=5
    )
    resp = client.describe_network_interfaces(NetworkInterfaceIds=[eni.id])
    my_eni = resp["NetworkInterfaces"][0]
    ips_before = [addr["PrivateIpAddress"] for addr in my_eni["PrivateIpAddresses"]]

    # Remove IP
    resp = client.unassign_private_ip_addresses(
        NetworkInterfaceId=eni.id, PrivateIpAddresses=[ips_before[1], ips_before[2]]
    )

    # Verify it's gone
    resp = client.describe_network_interfaces(NetworkInterfaceIds=[eni.id])
    my_eni = resp["NetworkInterfaces"][0]
    my_eni.should.have.key("PrivateIpAddresses").should.have.length_of(4)
    my_eni.should.have.key("PrivateIpAddresses").contain(
        {"Primary": True, "PrivateIpAddress": "54.0.0.1"}
    )
    my_eni.should.have.key("PrivateIpAddresses").contain(
        {"Primary": False, "PrivateIpAddress": ips_before[3]}
    )
    my_eni.should.have.key("PrivateIpAddresses").contain(
        {"Primary": False, "PrivateIpAddress": ips_before[4]}
    )
    my_eni.should.have.key("PrivateIpAddresses").contain(
        {"Primary": False, "PrivateIpAddress": ips_before[5]}
    )


@mock_ec2
def test_assign_ipv6_addresses__by_address():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    client = boto3.client("ec2", "us-east-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock="10.0.0.0/18")

    ipv6_orig = random_private_ip("2001:db8::/101", ipv6=True)
    ipv6_2 = random_private_ip("2001:db8::/101", ipv6=True)
    ipv6_3 = random_private_ip("2001:db8::/101", ipv6=True)
    eni = ec2.create_network_interface(
        SubnetId=subnet.id, Ipv6Addresses=[{"Ipv6Address": ipv6_orig}]
    )
    resp = client.describe_network_interfaces(NetworkInterfaceIds=[eni.id])
    my_eni = resp["NetworkInterfaces"][0]
    my_eni.should.have.key("Ipv6Addresses").equals([{"Ipv6Address": ipv6_orig}])

    client.assign_ipv6_addresses(
        NetworkInterfaceId=eni.id, Ipv6Addresses=[ipv6_2, ipv6_3]
    )

    resp = client.describe_network_interfaces(NetworkInterfaceIds=[eni.id])
    my_eni = resp["NetworkInterfaces"][0]
    my_eni.should.have.key("Ipv6Addresses").length_of(3)
    my_eni.should.have.key("Ipv6Addresses").should.contain({"Ipv6Address": ipv6_orig})
    my_eni.should.have.key("Ipv6Addresses").should.contain({"Ipv6Address": ipv6_2})
    my_eni.should.have.key("Ipv6Addresses").should.contain({"Ipv6Address": ipv6_3})


@mock_ec2
def test_assign_ipv6_addresses__by_count():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    client = boto3.client("ec2", "us-east-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="10.0.0.0/18", Ipv6CidrBlock="2001:db8::/64"
    )

    ipv6_orig = random_private_ip("2001:db8::/101", ipv6=True)
    eni = ec2.create_network_interface(
        SubnetId=subnet.id, Ipv6Addresses=[{"Ipv6Address": ipv6_orig}]
    )

    client.assign_ipv6_addresses(NetworkInterfaceId=eni.id, Ipv6AddressCount=3)

    resp = client.describe_network_interfaces(NetworkInterfaceIds=[eni.id])
    my_eni = resp["NetworkInterfaces"][0]
    my_eni.should.have.key("Ipv6Addresses").length_of(4)
    my_eni.should.have.key("Ipv6Addresses").should.contain({"Ipv6Address": ipv6_orig})


@mock_ec2
def test_assign_ipv6_addresses__by_address_and_count():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    client = boto3.client("ec2", "us-east-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="10.0.0.0/18", Ipv6CidrBlock="2001:db8::/64"
    )

    ipv6_orig = random_private_ip("2001:db8::/101", ipv6=True)
    ipv6_2 = random_private_ip("2001:db8::/101", ipv6=True)
    ipv6_3 = random_private_ip("2001:db8::/101", ipv6=True)
    eni = ec2.create_network_interface(
        SubnetId=subnet.id, Ipv6Addresses=[{"Ipv6Address": ipv6_orig}]
    )

    client.assign_ipv6_addresses(
        NetworkInterfaceId=eni.id, Ipv6Addresses=[ipv6_2, ipv6_3]
    )
    client.assign_ipv6_addresses(NetworkInterfaceId=eni.id, Ipv6AddressCount=2)

    resp = client.describe_network_interfaces(NetworkInterfaceIds=[eni.id])
    my_eni = resp["NetworkInterfaces"][0]
    my_eni.should.have.key("Ipv6Addresses").length_of(5)
    my_eni.should.have.key("Ipv6Addresses").should.contain({"Ipv6Address": ipv6_orig})
    my_eni.should.have.key("Ipv6Addresses").should.contain({"Ipv6Address": ipv6_2})
    my_eni.should.have.key("Ipv6Addresses").should.contain({"Ipv6Address": ipv6_3})


@mock_ec2
def test_unassign_ipv6_addresses():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    client = boto3.client("ec2", "us-east-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="10.0.0.0/18", Ipv6CidrBlock="2001:db8::/64"
    )

    ipv6_orig = random_private_ip("2001:db8::/101", ipv6=True)
    ipv6_2 = random_private_ip("2001:db8::/101", ipv6=True)
    ipv6_3 = random_private_ip("2001:db8::/101", ipv6=True)
    eni = ec2.create_network_interface(
        SubnetId=subnet.id, Ipv6Addresses=[{"Ipv6Address": ipv6_orig}]
    )

    client.assign_ipv6_addresses(
        NetworkInterfaceId=eni.id, Ipv6Addresses=[ipv6_2, ipv6_3]
    )

    client.unassign_ipv6_addresses(NetworkInterfaceId=eni.id, Ipv6Addresses=[ipv6_2])

    resp = client.describe_network_interfaces(NetworkInterfaceIds=[eni.id])
    my_eni = resp["NetworkInterfaces"][0]
    my_eni.should.have.key("Ipv6Addresses").length_of(2)
    my_eni.should.have.key("Ipv6Addresses").should.contain({"Ipv6Address": ipv6_orig})
    my_eni.should.have.key("Ipv6Addresses").should.contain({"Ipv6Address": ipv6_3})


@mock_ec2
def test_elastic_network_interfaces_describe_attachment():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    client = boto3.client("ec2", "us-east-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock="10.0.0.0/18")
    eni_id = subnet.create_network_interface(Description="A network interface").id
    instance_id = client.run_instances(ImageId="ami-12c6146b", MinCount=1, MaxCount=1)[
        "Instances"
    ][0]["InstanceId"]

    client.attach_network_interface(
        NetworkInterfaceId=eni_id, InstanceId=instance_id, DeviceIndex=1
    )

    my_eni_attachment = client.describe_network_interface_attribute(
        NetworkInterfaceId=eni_id, Attribute="attachment"
    ).get("Attachment")
    my_eni_attachment["InstanceId"].should.equal(instance_id)
    my_eni_attachment["DeleteOnTermination"].should.equal(False)

    with pytest.raises(ClientError) as ex:
        client.describe_network_interface_attribute(
            NetworkInterfaceId=eni_id, Attribute="attach"
        )
    ex.value.response["Error"]["Code"].should.equal("InvalidParameterValue")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["Error"]["Message"].should.equal(
        "Value (attach) for parameter attribute is invalid. Unknown attribute."
    )

    with pytest.raises(ClientError) as ex:
        client.describe_network_interface_attribute(
            NetworkInterfaceId=eni_id, Attribute="attachment", DryRun=True
        )
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the DescribeNetworkInterfaceAttribute operation: Request would have succeeded, but DryRun flag is set"
    )

    my_eni_description = client.describe_network_interface_attribute(
        NetworkInterfaceId=eni_id, Attribute="description"
    ).get("Description")
    my_eni_description["Value"].should.be.equal("A network interface")

    my_eni_source_dest_check = client.describe_network_interface_attribute(
        NetworkInterfaceId=eni_id, Attribute="sourceDestCheck"
    ).get("SourceDestCheck")
    my_eni_source_dest_check["Value"].should.be.equal(True)
