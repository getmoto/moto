import boto3
import sure  # noqa
from moto import mock_ec2, settings
from moto.core import ACCOUNT_ID
from unittest import SkipTest


@mock_ec2
def test_describe_transit_gateway_peering_attachment_empty():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("ServerMode is not guaranteed to be empty")
    ec2 = boto3.client("ec2", region_name="us-west-1")

    all_attachments = ec2.describe_transit_gateway_peering_attachments()[
        "TransitGatewayPeeringAttachments"
    ]
    all_attachments.should.equal([])


@mock_ec2
def test_create_and_describe_transit_gateway_peering_attachment():
    ec2 = boto3.client("ec2", region_name="us-west-1")
    gateway_id1 = ec2.create_transit_gateway(Description="my first gateway")[
        "TransitGateway"
    ]["TransitGatewayId"]
    gateway_id2 = ec2.create_transit_gateway(Description="my second gateway")[
        "TransitGateway"
    ]["TransitGatewayId"]
    response = ec2.create_transit_gateway_peering_attachment(
        TransitGatewayId=gateway_id1,
        PeerTransitGatewayId=gateway_id2,
        PeerAccountId=ACCOUNT_ID,
        PeerRegion="us-east-1",
    )
    response.should.have.key("TransitGatewayPeeringAttachment")
    attachment = response["TransitGatewayPeeringAttachment"]
    attachment.should.have.key("TransitGatewayAttachmentId").match(
        "tgw-attach-[a-z0-9]+"
    )
    attachment["RequesterTgwInfo"]["TransitGatewayId"].should.equal(gateway_id1)
    attachment["AccepterTgwInfo"]["TransitGatewayId"].should.equal(gateway_id2)

    all_attachments = ec2.describe_transit_gateway_peering_attachments()[
        "TransitGatewayPeeringAttachments"
    ]
    our_attachment = [
        att
        for att in all_attachments
        if att["TransitGatewayAttachmentId"] == attachment["TransitGatewayAttachmentId"]
    ]
    our_attachment.should.equal([attachment])


@mock_ec2
def test_describe_transit_gateway_peering_attachment_by_filters():
    ec2 = boto3.client("ec2", region_name="us-west-1")
    gateway_id1 = ec2.create_transit_gateway(Description="my first gateway")[
        "TransitGateway"
    ]["TransitGatewayId"]
    gateway_id2 = ec2.create_transit_gateway(Description="my second gateway")[
        "TransitGateway"
    ]["TransitGatewayId"]
    gateway_id3 = ec2.create_transit_gateway(Description="my second gateway")[
        "TransitGateway"
    ]["TransitGatewayId"]
    attchmnt1 = create_peering_attachment(ec2, gateway_id1, gateway_id2)
    attchmnt2 = create_peering_attachment(ec2, gateway_id1, gateway_id3)
    attchmnt3 = create_peering_attachment(ec2, gateway_id2, gateway_id3)

    all_attachments = ec2.describe_transit_gateway_peering_attachments()[
        "TransitGatewayPeeringAttachments"
    ]
    ours = [
        a
        for a in all_attachments
        if a["TransitGatewayAttachmentId"] in [attchmnt1, attchmnt2, attchmnt3]
    ]
    ours.should.have.length_of(3)

    find_1 = ec2.describe_transit_gateway_peering_attachments(
        TransitGatewayAttachmentIds=[attchmnt1]
    )["TransitGatewayPeeringAttachments"]
    [a["TransitGatewayAttachmentId"] for a in find_1].should.equal([attchmnt1])

    find_1_3 = ec2.describe_transit_gateway_peering_attachments(
        TransitGatewayAttachmentIds=[attchmnt1, attchmnt3]
    )["TransitGatewayPeeringAttachments"]
    [a["TransitGatewayAttachmentId"] for a in find_1_3].should.equal(
        [attchmnt1, attchmnt3]
    )

    find_3 = ec2.describe_transit_gateway_peering_attachments(
        Filters=[{"Name": "transit-gateway-attachment-id", "Values": [attchmnt3]}]
    )["TransitGatewayPeeringAttachments"]
    [a["TransitGatewayAttachmentId"] for a in find_3].should.equal([attchmnt3])

    filters = [{"Name": "state", "Values": ["available"]}]
    find_all = retrieve_all_attachments(ec2, filters)
    all_ids = [a["TransitGatewayAttachmentId"] for a in find_all]
    all_ids.should.contain(attchmnt1)
    all_ids.should.contain(attchmnt2)
    all_ids.should.contain(attchmnt3)

    find_none = ec2.describe_transit_gateway_peering_attachments(
        Filters=[{"Name": "state", "Values": ["unknown"]}]
    )["TransitGatewayPeeringAttachments"]
    find_none.should.equal([])

    ec2.reject_transit_gateway_peering_attachment(TransitGatewayAttachmentId=attchmnt2)

    find_available = ec2.describe_transit_gateway_peering_attachments(
        TransitGatewayAttachmentIds=[attchmnt1, attchmnt2],
        Filters=[{"Name": "state", "Values": ["available"]}],
    )["TransitGatewayPeeringAttachments"]
    [a["TransitGatewayAttachmentId"] for a in find_available].should.equal([attchmnt1])


@mock_ec2
def test_create_and_accept_transit_gateway_peering_attachment():
    ec2 = boto3.client("ec2", region_name="us-west-1")
    gateway_id1 = ec2.create_transit_gateway(Description="my first gateway")[
        "TransitGateway"
    ]["TransitGatewayId"]
    gateway_id2 = ec2.create_transit_gateway(Description="my second gateway")[
        "TransitGateway"
    ]["TransitGatewayId"]
    attchment_id = create_peering_attachment(ec2, gateway_id1, gateway_id2)

    ec2.accept_transit_gateway_peering_attachment(
        TransitGatewayAttachmentId=attchment_id
    )

    attachment = ec2.describe_transit_gateway_peering_attachments(
        TransitGatewayAttachmentIds=[attchment_id]
    )["TransitGatewayPeeringAttachments"][0]
    attachment.should.have.key("TransitGatewayAttachmentId").equal(attchment_id)
    attachment.should.have.key("State").equal("available")


@mock_ec2
def test_create_and_reject_transit_gateway_peering_attachment():
    ec2 = boto3.client("ec2", region_name="us-west-1")
    gateway_id1 = ec2.create_transit_gateway(Description="my first gateway")[
        "TransitGateway"
    ]["TransitGatewayId"]
    gateway_id2 = ec2.create_transit_gateway(Description="my second gateway")[
        "TransitGateway"
    ]["TransitGatewayId"]
    attchment_id = create_peering_attachment(ec2, gateway_id1, gateway_id2)

    ec2.reject_transit_gateway_peering_attachment(
        TransitGatewayAttachmentId=attchment_id
    )

    attachment = ec2.describe_transit_gateway_peering_attachments(
        TransitGatewayAttachmentIds=[attchment_id]
    )["TransitGatewayPeeringAttachments"][0]
    attachment.should.have.key("TransitGatewayAttachmentId").equal(attchment_id)
    attachment.should.have.key("State").equal("rejected")


@mock_ec2
def test_create_and_delete_transit_gateway_peering_attachment():
    ec2 = boto3.client("ec2", region_name="us-west-1")
    gateway_id1 = ec2.create_transit_gateway(Description="my first gateway")[
        "TransitGateway"
    ]["TransitGatewayId"]
    gateway_id2 = ec2.create_transit_gateway(Description="my second gateway")[
        "TransitGateway"
    ]["TransitGatewayId"]
    attchment_id = create_peering_attachment(ec2, gateway_id1, gateway_id2)

    ec2.delete_transit_gateway_peering_attachment(
        TransitGatewayAttachmentId=attchment_id
    )

    attachment = ec2.describe_transit_gateway_peering_attachments(
        TransitGatewayAttachmentIds=[attchment_id]
    )["TransitGatewayPeeringAttachments"][0]
    attachment.should.have.key("TransitGatewayAttachmentId").equal(attchment_id)
    attachment.should.have.key("State").equal("deleted")


def create_peering_attachment(ec2, gateway_id1, gateway_id2):
    return ec2.create_transit_gateway_peering_attachment(
        TransitGatewayId=gateway_id1,
        PeerTransitGatewayId=gateway_id2,
        PeerAccountId=ACCOUNT_ID,
        PeerRegion="us-east-1",
    )["TransitGatewayPeeringAttachment"]["TransitGatewayAttachmentId"]


def retrieve_all_attachments(client, filters=[]):
    resp = client.describe_transit_gateway_peering_attachments(Filters=filters)
    attmnts = resp["TransitGatewayPeeringAttachments"]
    token = resp.get("NextToken")
    while token:
        resp = client.describe_transit_gateway_peering_attachments(
            Filters=filters, NextToken=token
        )
        attmnts.extend(resp["TransitGatewayPeeringAttachments"])
        token = resp.get("NextToken")
    return attmnts
