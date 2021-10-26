import pytest

import boto
import boto3

from boto.exception import EC2ResponseError
from botocore.exceptions import ClientError

import sure  # noqa # pylint: disable=unused-import

from moto import mock_ec2_deprecated, mock_ec2
from uuid import uuid4


VPC_CIDR = "10.0.0.0/16"
BAD_VPC = "vpc-deadbeef"
BAD_IGW = "igw-deadbeef"


# Has boto3 equivalent
@mock_ec2_deprecated
def test_igw_create():
    """internet gateway create"""
    conn = boto.connect_vpc("the_key", "the_secret")

    conn.get_all_internet_gateways().should.have.length_of(0)

    with pytest.raises(EC2ResponseError) as ex:
        igw = conn.create_internet_gateway(dry_run=True)
    ex.value.error_code.should.equal("DryRunOperation")
    ex.value.status.should.equal(412)
    ex.value.message.should.equal(
        "An error occurred (DryRunOperation) when calling the CreateInternetGateway operation: Request would have succeeded, but DryRun flag is set"
    )

    igw = conn.create_internet_gateway()
    conn.get_all_internet_gateways().should.have.length_of(1)
    igw.id.should.match(r"igw-[0-9a-f]+")

    igw = conn.get_all_internet_gateways()[0]
    igw.attachments.should.have.length_of(0)


@mock_ec2
def test_igw_create_boto3():
    """ internet gateway create """
    ec2 = boto3.resource("ec2", "us-west-1")
    client = boto3.client("ec2", "us-west-1")

    with pytest.raises(ClientError) as ex:
        client.create_internet_gateway(DryRun=True)
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the CreateInternetGateway operation: Request would have succeeded, but DryRun flag is set"
    )

    igw = ec2.create_internet_gateway()
    igw.id.should.match(r"igw-[0-9a-f]+")

    igw = client.describe_internet_gateways(InternetGatewayIds=[igw.id])[
        "InternetGateways"
    ][0]
    igw["Attachments"].should.have.length_of(0)


# Has boto3 equivalent
@mock_ec2_deprecated
def test_igw_attach():
    """internet gateway attach"""
    conn = boto.connect_vpc("the_key", "the_secret")
    igw = conn.create_internet_gateway()
    vpc = conn.create_vpc(VPC_CIDR)

    with pytest.raises(EC2ResponseError) as ex:
        conn.attach_internet_gateway(igw.id, vpc.id, dry_run=True)
    ex.value.error_code.should.equal("DryRunOperation")
    ex.value.status.should.equal(412)
    ex.value.message.should.equal(
        "An error occurred (DryRunOperation) when calling the AttachInternetGateway operation: Request would have succeeded, but DryRun flag is set"
    )

    conn.attach_internet_gateway(igw.id, vpc.id)

    igw = conn.get_all_internet_gateways()[0]
    igw.attachments[0].vpc_id.should.be.equal(vpc.id)


@mock_ec2
def test_igw_attach_boto3():
    """ internet gateway attach """
    ec2 = boto3.resource("ec2", "us-west-1")
    client = boto3.client("ec2", "us-west-1")

    igw = ec2.create_internet_gateway()
    vpc = ec2.create_vpc(CidrBlock=VPC_CIDR)

    with pytest.raises(ClientError) as ex:
        vpc.attach_internet_gateway(InternetGatewayId=igw.id, DryRun=True)
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the AttachInternetGateway operation: Request would have succeeded, but DryRun flag is set"
    )

    vpc.attach_internet_gateway(InternetGatewayId=igw.id)

    igw = client.describe_internet_gateways(InternetGatewayIds=[igw.id])[
        "InternetGateways"
    ][0]
    igw["Attachments"].should.equal([{"State": "available", "VpcId": vpc.id}])


# Has boto3 equivalent
@mock_ec2_deprecated
def test_igw_attach_bad_vpc():
    """internet gateway fail to attach w/ bad vpc"""
    conn = boto.connect_vpc("the_key", "the_secret")
    igw = conn.create_internet_gateway()

    with pytest.raises(EC2ResponseError) as cm:
        conn.attach_internet_gateway(igw.id, BAD_VPC)
    cm.value.code.should.equal("InvalidVpcID.NotFound")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none


@mock_ec2
def test_igw_attach_bad_vpc_boto3():
    """ internet gateway fail to attach w/ bad vpc """
    ec2 = boto3.resource("ec2", "us-west-1")
    igw = ec2.create_internet_gateway()

    with pytest.raises(ClientError) as ex:
        igw.attach_to_vpc(VpcId=BAD_VPC)
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("InvalidVpcID.NotFound")


# Has boto3 equivalent
@mock_ec2_deprecated
def test_igw_attach_twice():
    """internet gateway fail to attach twice"""
    conn = boto.connect_vpc("the_key", "the_secret")
    igw = conn.create_internet_gateway()
    vpc1 = conn.create_vpc(VPC_CIDR)
    vpc2 = conn.create_vpc(VPC_CIDR)
    conn.attach_internet_gateway(igw.id, vpc1.id)

    with pytest.raises(EC2ResponseError) as cm:
        conn.attach_internet_gateway(igw.id, vpc2.id)
    cm.value.code.should.equal("Resource.AlreadyAssociated")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none


@mock_ec2
def test_igw_attach_twice_boto3():
    """ internet gateway fail to attach twice """
    ec2 = boto3.resource("ec2", "us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")
    igw = ec2.create_internet_gateway()
    vpc1 = ec2.create_vpc(CidrBlock=VPC_CIDR)
    vpc2 = ec2.create_vpc(CidrBlock=VPC_CIDR)
    client.attach_internet_gateway(InternetGatewayId=igw.id, VpcId=vpc1.id)

    with pytest.raises(ClientError) as ex:
        client.attach_internet_gateway(InternetGatewayId=igw.id, VpcId=vpc2.id)
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("Resource.AlreadyAssociated")


# Has boto3 equivalent
@mock_ec2_deprecated
def test_igw_detach():
    """internet gateway detach"""
    conn = boto.connect_vpc("the_key", "the_secret")
    igw = conn.create_internet_gateway()
    vpc = conn.create_vpc(VPC_CIDR)
    conn.attach_internet_gateway(igw.id, vpc.id)

    with pytest.raises(EC2ResponseError) as ex:
        conn.detach_internet_gateway(igw.id, vpc.id, dry_run=True)
    ex.value.error_code.should.equal("DryRunOperation")
    ex.value.status.should.equal(412)
    ex.value.message.should.equal(
        "An error occurred (DryRunOperation) when calling the DetachInternetGateway operation: Request would have succeeded, but DryRun flag is set"
    )

    conn.detach_internet_gateway(igw.id, vpc.id)
    igw = conn.get_all_internet_gateways()[0]
    igw.attachments.should.have.length_of(0)


@mock_ec2
def test_igw_detach_boto3():
    """ internet gateway detach"""
    ec2 = boto3.resource("ec2", "us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")
    igw = ec2.create_internet_gateway()
    vpc = ec2.create_vpc(CidrBlock=VPC_CIDR)
    client.attach_internet_gateway(InternetGatewayId=igw.id, VpcId=vpc.id)

    with pytest.raises(ClientError) as ex:
        client.detach_internet_gateway(
            InternetGatewayId=igw.id, VpcId=vpc.id, DryRun=True
        )
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the DetachInternetGateway operation: Request would have succeeded, but DryRun flag is set"
    )

    client.detach_internet_gateway(InternetGatewayId=igw.id, VpcId=vpc.id)
    igw = igw = client.describe_internet_gateways(InternetGatewayIds=[igw.id])[
        "InternetGateways"
    ][0]
    igw["Attachments"].should.have.length_of(0)


# Has boto3 equivalent
@mock_ec2_deprecated
def test_igw_detach_wrong_vpc():
    """internet gateway fail to detach w/ wrong vpc"""
    conn = boto.connect_vpc("the_key", "the_secret")
    igw = conn.create_internet_gateway()
    vpc1 = conn.create_vpc(VPC_CIDR)
    vpc2 = conn.create_vpc(VPC_CIDR)
    conn.attach_internet_gateway(igw.id, vpc1.id)

    with pytest.raises(EC2ResponseError) as cm:
        conn.detach_internet_gateway(igw.id, vpc2.id)
    cm.value.code.should.equal("Gateway.NotAttached")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none


@mock_ec2
def test_igw_detach_wrong_vpc_boto3():
    """ internet gateway fail to detach w/ wrong vpc """
    ec2 = boto3.resource("ec2", "us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")
    igw = ec2.create_internet_gateway()
    vpc1 = ec2.create_vpc(CidrBlock=VPC_CIDR)
    vpc2 = ec2.create_vpc(CidrBlock=VPC_CIDR)
    client.attach_internet_gateway(InternetGatewayId=igw.id, VpcId=vpc1.id)

    with pytest.raises(ClientError) as ex:
        client.detach_internet_gateway(InternetGatewayId=igw.id, VpcId=vpc2.id)
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("Gateway.NotAttached")


# Has boto3 equivalent
@mock_ec2_deprecated
def test_igw_detach_invalid_vpc():
    """internet gateway fail to detach w/ invalid vpc"""
    conn = boto.connect_vpc("the_key", "the_secret")
    igw = conn.create_internet_gateway()
    vpc = conn.create_vpc(VPC_CIDR)
    conn.attach_internet_gateway(igw.id, vpc.id)

    with pytest.raises(EC2ResponseError) as cm:
        conn.detach_internet_gateway(igw.id, BAD_VPC)
    cm.value.code.should.equal("Gateway.NotAttached")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none


@mock_ec2
def test_igw_detach_invalid_vpc_boto3():
    """ internet gateway fail to detach w/ invalid vpc """
    ec2 = boto3.resource("ec2", "us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")
    igw = ec2.create_internet_gateway()
    vpc = ec2.create_vpc(CidrBlock=VPC_CIDR)
    client.attach_internet_gateway(InternetGatewayId=igw.id, VpcId=vpc.id)

    with pytest.raises(ClientError) as ex:
        client.detach_internet_gateway(InternetGatewayId=igw.id, VpcId=BAD_VPC)
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("Gateway.NotAttached")


# Has boto3 equivalent
@mock_ec2_deprecated
def test_igw_detach_unattached():
    """internet gateway fail to detach unattached"""
    conn = boto.connect_vpc("the_key", "the_secret")
    igw = conn.create_internet_gateway()
    vpc = conn.create_vpc(VPC_CIDR)

    with pytest.raises(EC2ResponseError) as cm:
        conn.detach_internet_gateway(igw.id, vpc.id)
    cm.value.code.should.equal("Gateway.NotAttached")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none


@mock_ec2
def test_igw_detach_unattached_boto3():
    """ internet gateway fail to detach unattached """
    ec2 = boto3.resource("ec2", "us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")
    igw = ec2.create_internet_gateway()
    vpc = ec2.create_vpc(CidrBlock=VPC_CIDR)

    with pytest.raises(ClientError) as ex:
        client.detach_internet_gateway(InternetGatewayId=igw.id, VpcId=vpc.id)
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("Gateway.NotAttached")


# Has boto3 equivalent
@mock_ec2_deprecated
def test_igw_delete():
    """internet gateway delete"""
    conn = boto.connect_vpc("the_key", "the_secret")
    conn.create_vpc(VPC_CIDR)
    conn.get_all_internet_gateways().should.have.length_of(0)
    igw = conn.create_internet_gateway()
    conn.get_all_internet_gateways().should.have.length_of(1)

    with pytest.raises(EC2ResponseError) as ex:
        conn.delete_internet_gateway(igw.id, dry_run=True)
    ex.value.error_code.should.equal("DryRunOperation")
    ex.value.status.should.equal(412)
    ex.value.message.should.equal(
        "An error occurred (DryRunOperation) when calling the DeleteInternetGateway operation: Request would have succeeded, but DryRun flag is set"
    )

    conn.delete_internet_gateway(igw.id)
    conn.get_all_internet_gateways().should.have.length_of(0)


@mock_ec2
def test_igw_delete_boto3():
    """ internet gateway delete"""
    ec2 = boto3.resource("ec2", "us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")
    ec2.create_vpc(CidrBlock=VPC_CIDR)

    igw = ec2.create_internet_gateway()
    [i["InternetGatewayId"] for i in (retrieve_all(client))].should.contain(igw.id)

    with pytest.raises(ClientError) as ex:
        client.delete_internet_gateway(InternetGatewayId=igw.id, DryRun=True)
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the DeleteInternetGateway operation: Request would have succeeded, but DryRun flag is set"
    )

    client.delete_internet_gateway(InternetGatewayId=igw.id)
    [i["InternetGatewayId"] for i in (retrieve_all(client))].shouldnt.contain(igw.id)


# Has boto3 equivalent
@mock_ec2_deprecated
def test_igw_delete_attached():
    """internet gateway fail to delete attached"""
    conn = boto.connect_vpc("the_key", "the_secret")
    igw = conn.create_internet_gateway()
    vpc = conn.create_vpc(VPC_CIDR)
    conn.attach_internet_gateway(igw.id, vpc.id)

    with pytest.raises(EC2ResponseError) as cm:
        conn.delete_internet_gateway(igw.id)
    cm.value.code.should.equal("DependencyViolation")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none


@mock_ec2
def test_igw_delete_attached_boto3():
    """ internet gateway fail to delete attached """
    ec2 = boto3.resource("ec2", "us-west-1")
    client = boto3.client("ec2", "us-west-1")
    igw = ec2.create_internet_gateway()
    vpc = ec2.create_vpc(CidrBlock=VPC_CIDR)
    client.attach_internet_gateway(InternetGatewayId=igw.id, VpcId=vpc.id)

    with pytest.raises(ClientError) as ex:
        client.delete_internet_gateway(InternetGatewayId=igw.id)
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("DependencyViolation")


# Has boto3 equivalent
@mock_ec2_deprecated
def test_igw_desribe():
    """internet gateway fetch by id"""
    conn = boto.connect_vpc("the_key", "the_secret")
    igw = conn.create_internet_gateway()
    igw_by_search = conn.get_all_internet_gateways([igw.id])[0]
    igw.id.should.equal(igw_by_search.id)


@mock_ec2
def test_igw_describe_boto3():
    """ internet gateway fetch by id """
    ec2 = boto3.resource("ec2", "us-west-1")
    client = boto3.client("ec2", "us-west-1")
    igw = ec2.create_internet_gateway()
    igw_by_search = client.describe_internet_gateways(InternetGatewayIds=[igw.id])[
        "InternetGateways"
    ][0]
    igw.id.should.equal(igw_by_search["InternetGatewayId"])


# Has boto3 equivalent
@mock_ec2_deprecated
def test_igw_describe_bad_id():
    """internet gateway fail to fetch by bad id"""
    conn = boto.connect_vpc("the_key", "the_secret")
    with pytest.raises(EC2ResponseError) as cm:
        conn.get_all_internet_gateways([BAD_IGW])
    cm.value.code.should.equal("InvalidInternetGatewayID.NotFound")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none


@mock_ec2
def test_igw_describe_bad_id_boto3():
    """ internet gateway fail to fetch by bad id """
    client = boto3.client("ec2", "us-west-1")
    with pytest.raises(ClientError) as ex:
        client.describe_internet_gateways(InternetGatewayIds=[BAD_IGW])
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("InvalidInternetGatewayID.NotFound")


# Has boto3 equivalent
@mock_ec2_deprecated
def test_igw_filter_by_vpc_id():
    """internet gateway filter by vpc id"""
    conn = boto.connect_vpc("the_key", "the_secret")

    igw1 = conn.create_internet_gateway()
    conn.create_internet_gateway()
    vpc = conn.create_vpc(VPC_CIDR)
    conn.attach_internet_gateway(igw1.id, vpc.id)

    result = conn.get_all_internet_gateways(filters={"attachment.vpc-id": vpc.id})
    result.should.have.length_of(1)
    result[0].id.should.equal(igw1.id)


@mock_ec2
def test_igw_filter_by_vpc_id_boto3():
    """ internet gateway filter by vpc id """
    ec2 = boto3.resource("ec2", "us-west-1")
    client = boto3.client("ec2", "us-west-1")

    igw1 = ec2.create_internet_gateway()
    ec2.create_internet_gateway()
    vpc = ec2.create_vpc(CidrBlock=VPC_CIDR)
    client.attach_internet_gateway(InternetGatewayId=igw1.id, VpcId=vpc.id)

    result = client.describe_internet_gateways(
        Filters=[{"Name": "attachment.vpc-id", "Values": [vpc.id]}]
    )
    result["InternetGateways"].should.have.length_of(1)
    result["InternetGateways"][0]["InternetGatewayId"].should.equal(igw1.id)


# Has boto3 equivalent
@mock_ec2_deprecated
def test_igw_filter_by_tags():
    """internet gateway filter by vpc id"""
    conn = boto.connect_vpc("the_key", "the_secret")

    igw1 = conn.create_internet_gateway()
    conn.create_internet_gateway()
    igw1.add_tag("tests", "yes")

    result = conn.get_all_internet_gateways(filters={"tag:tests": "yes"})
    result.should.have.length_of(1)
    result[0].id.should.equal(igw1.id)


@mock_ec2
def test_igw_filter_by_tags_boto3():
    """ internet gateway filter by vpc id """
    ec2 = boto3.resource("ec2", "us-west-1")
    client = boto3.client("ec2", "us-west-1")

    igw1 = ec2.create_internet_gateway()
    ec2.create_internet_gateway()
    tag_value = str(uuid4())
    igw1.create_tags(Tags=[{"Key": "tests", "Value": tag_value}])

    result = retrieve_all(client, [{"Name": "tag:tests", "Values": [tag_value]}])
    result.should.have.length_of(1)
    result[0]["InternetGatewayId"].should.equal(igw1.id)


# Has boto3 equivalent
@mock_ec2_deprecated
def test_igw_filter_by_internet_gateway_id():
    """internet gateway filter by internet gateway id"""
    conn = boto.connect_vpc("the_key", "the_secret")

    igw1 = conn.create_internet_gateway()
    conn.create_internet_gateway()

    result = conn.get_all_internet_gateways(filters={"internet-gateway-id": igw1.id})
    result.should.have.length_of(1)
    result[0].id.should.equal(igw1.id)


@mock_ec2
def test_igw_filter_by_internet_gateway_id_boto3():
    """ internet gateway filter by internet gateway id """
    ec2 = boto3.resource("ec2", "us-west-1")
    client = boto3.client("ec2", "us-west-1")

    igw1 = ec2.create_internet_gateway()
    ec2.create_internet_gateway()

    result = client.describe_internet_gateways(
        Filters=[{"Name": "internet-gateway-id", "Values": [igw1.id]}]
    )
    result["InternetGateways"].should.have.length_of(1)
    result["InternetGateways"][0]["InternetGatewayId"].should.equal(igw1.id)


# Has boto3 equivalent
@mock_ec2_deprecated
def test_igw_filter_by_attachment_state():
    """internet gateway filter by attachment state"""
    conn = boto.connect_vpc("the_key", "the_secret")

    igw1 = conn.create_internet_gateway()
    conn.create_internet_gateway()
    vpc = conn.create_vpc(VPC_CIDR)
    conn.attach_internet_gateway(igw1.id, vpc.id)

    result = conn.get_all_internet_gateways(filters={"attachment.state": "available"})
    result.should.have.length_of(1)
    result[0].id.should.equal(igw1.id)


@mock_ec2
def test_igw_filter_by_attachment_state_boto3():
    """ internet gateway filter by attachment state """
    ec2 = boto3.resource("ec2", "us-west-1")
    client = boto3.client("ec2", "us-west-1")

    igw1 = ec2.create_internet_gateway()
    igw2 = ec2.create_internet_gateway()
    vpc = ec2.create_vpc(CidrBlock=VPC_CIDR)
    client.attach_internet_gateway(InternetGatewayId=igw1.id, VpcId=vpc.id)

    filters = [{"Name": "attachment.state", "Values": ["available"]}]
    all_ids = [igw["InternetGatewayId"] for igw in (retrieve_all(client, filters))]
    all_ids.should.contain(igw1.id)
    all_ids.shouldnt.contain(igw2.id)


@mock_ec2
def test_create_internet_gateway_with_tags():
    ec2 = boto3.resource("ec2", region_name="eu-central-1")

    igw = ec2.create_internet_gateway(
        TagSpecifications=[
            {
                "ResourceType": "internet-gateway",
                "Tags": [{"Key": "test", "Value": "TestRouteTable"}],
            }
        ],
    )
    igw.tags.should.have.length_of(1)
    igw.tags.should.equal([{"Key": "test", "Value": "TestRouteTable"}])


def retrieve_all(client, filters=[]):  # pylint: disable=W0102
    resp = client.describe_internet_gateways(Filters=filters)
    all_igws = resp["InternetGateways"]
    token = resp.get("NextToken")
    while token:
        resp = client.describe_internet_gateways(NextToken=token, Filters=filters)
        all_igws.extend(resp["InternetGateways"])
        token = resp.get("NextToken")
    return all_igws
