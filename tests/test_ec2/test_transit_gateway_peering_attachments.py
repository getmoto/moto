import os
from unittest import SkipTest, mock

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws, settings
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID


@mock_aws
def test_describe_transit_gateway_peering_attachment_empty():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("ServerMode is not guaranteed to be empty")
    ec2 = boto3.client("ec2", region_name="us-west-1")

    all_attachments = ec2.describe_transit_gateway_peering_attachments()[
        "TransitGatewayPeeringAttachments"
    ]
    assert all_attachments == []


@mock_aws
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
    assert "TransitGatewayPeeringAttachment" in response
    attachment = response["TransitGatewayPeeringAttachment"]
    assert attachment["TransitGatewayAttachmentId"].startswith("tgw-attach-")
    assert attachment["RequesterTgwInfo"]["TransitGatewayId"] == gateway_id1
    assert attachment["AccepterTgwInfo"]["TransitGatewayId"] == gateway_id2

    all_attachments = ec2.describe_transit_gateway_peering_attachments()[
        "TransitGatewayPeeringAttachments"
    ]
    our_attachment = [
        att
        for att in all_attachments
        if att["TransitGatewayAttachmentId"] == attachment["TransitGatewayAttachmentId"]
    ]
    assert our_attachment == [attachment]


@mock_aws
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
    assert len(ours) == 3

    find_1 = ec2.describe_transit_gateway_peering_attachments(
        TransitGatewayAttachmentIds=[attchmnt1]
    )["TransitGatewayPeeringAttachments"]
    assert [a["TransitGatewayAttachmentId"] for a in find_1] == [attchmnt1]

    find_1_3 = ec2.describe_transit_gateway_peering_attachments(
        TransitGatewayAttachmentIds=[attchmnt1, attchmnt3]
    )["TransitGatewayPeeringAttachments"]
    assert [a["TransitGatewayAttachmentId"] for a in find_1_3] == [attchmnt1, attchmnt3]

    find_3 = ec2.describe_transit_gateway_peering_attachments(
        Filters=[{"Name": "transit-gateway-attachment-id", "Values": [attchmnt3]}]
    )["TransitGatewayPeeringAttachments"]
    assert [a["TransitGatewayAttachmentId"] for a in find_3] == [attchmnt3]

    filters = [{"Name": "state", "Values": ["pendingAcceptance"]}]
    find_all = retrieve_all_attachments(ec2, filters)
    all_ids = [a["TransitGatewayAttachmentId"] for a in find_all]
    assert attchmnt1 in all_ids
    assert attchmnt2 in all_ids
    assert attchmnt3 in all_ids

    find_none = ec2.describe_transit_gateway_peering_attachments(
        Filters=[{"Name": "state", "Values": ["unknown"]}]
    )["TransitGatewayPeeringAttachments"]
    assert find_none == []

    ec2.reject_transit_gateway_peering_attachment(TransitGatewayAttachmentId=attchmnt2)

    find_available = ec2.describe_transit_gateway_peering_attachments(
        TransitGatewayAttachmentIds=[attchmnt1, attchmnt2],
        Filters=[{"Name": "state", "Values": ["pendingAcceptance"]}],
    )["TransitGatewayPeeringAttachments"]
    assert [a["TransitGatewayAttachmentId"] for a in find_available] == [attchmnt1]


@mock_aws
def test_create_and_accept_transit_gateway_peering_attachment():
    ec2 = boto3.client("ec2", region_name="us-west-1")
    gateway_id1 = ec2.create_transit_gateway(Description="my first gateway")[
        "TransitGateway"
    ]["TransitGatewayId"]
    gateway_id2 = ec2.create_transit_gateway(Description="my second gateway")[
        "TransitGateway"
    ]["TransitGatewayId"]
    attchment_id = create_peering_attachment(
        ec2, gateway_id1, gateway_id2, peer_region="us-west-1"
    )

    ec2.accept_transit_gateway_peering_attachment(
        TransitGatewayAttachmentId=attchment_id
    )

    attachment = ec2.describe_transit_gateway_peering_attachments(
        TransitGatewayAttachmentIds=[attchment_id]
    )["TransitGatewayPeeringAttachments"][0]
    assert attachment["TransitGatewayAttachmentId"] == attchment_id
    assert attachment["State"] == "available"


@mock_aws
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
    assert attachment["TransitGatewayAttachmentId"] == attchment_id
    assert attachment["State"] == "rejected"


@mock_aws
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
    assert attachment["TransitGatewayAttachmentId"] == attchment_id
    assert attachment["State"] == "deleted"


@mock_aws
@pytest.mark.parametrize(
    "account1,account2",
    [
        pytest.param("111111111111", "111111111111", id="within account"),
        pytest.param("111111111111", "222222222222", id="across accounts"),
    ],
)
@pytest.mark.skipif(
    settings.TEST_SERVER_MODE, reason="Cannot set account ID in server mode"
)
def test_transit_gateway_peering_attachments_cross_region(account1, account2):
    # create transit gateways
    with mock.patch.dict(os.environ, {"MOTO_ACCOUNT_ID": account1}):
        ec2_us = boto3.client("ec2", "us-west-1")
        gateway_us = ec2_us.create_transit_gateway()["TransitGateway"][
            "TransitGatewayId"
        ]

    with mock.patch.dict(os.environ, {"MOTO_ACCOUNT_ID": account2}):
        ec2_eu = boto3.client("ec2", "eu-central-1")
        gateway_eu = ec2_eu.create_transit_gateway()["TransitGateway"][
            "TransitGatewayId"
        ]

    # create peering
    with mock.patch.dict(os.environ, {"MOTO_ACCOUNT_ID": account1}):
        attachment_id = create_peering_attachment(
            ec2_us,
            gateway_us,
            gateway_eu,
            peer_account=account2,
            peer_region="eu-central-1",
        )

    # ensure peering can be described by the accepter
    with mock.patch.dict(os.environ, {"MOTO_ACCOUNT_ID": account2}):
        response = ec2_eu.describe_transit_gateway_peering_attachments(
            TransitGatewayAttachmentIds=[attachment_id]
        )["TransitGatewayPeeringAttachments"][0]
        assert response["TransitGatewayAttachmentId"] == attachment_id
        assert response["RequesterTgwInfo"]["OwnerId"] == account1
        assert response["RequesterTgwInfo"]["Region"] == "us-west-1"
        assert response["AccepterTgwInfo"]["OwnerId"] == account2
        assert response["AccepterTgwInfo"]["Region"] == "eu-central-1"

    # ensure accepting in requester account/region raises
    with mock.patch.dict(os.environ, {"MOTO_ACCOUNT_ID": account1}):
        with pytest.raises(ClientError) as exc:
            ec2_us.accept_transit_gateway_peering_attachment(
                TransitGatewayAttachmentId=attachment_id
            )
        assert exc.value.response["Error"]["Code"] == "InvalidParameterValue"
        assert (
            exc.value.response["Error"]["Message"]
            == f"Cannot accept {attachment_id} as the source of the peering request."
        )

    with mock.patch.dict(os.environ, {"MOTO_ACCOUNT_ID": account2}):
        # ensure peering can be accepted by the accepter
        response = ec2_eu.accept_transit_gateway_peering_attachment(
            TransitGatewayAttachmentId=attachment_id
        )
        assert response["TransitGatewayPeeringAttachment"]["State"] == "available"

        # ensure peering can be deleted by the accepter
        response = ec2_eu.delete_transit_gateway_peering_attachment(
            TransitGatewayAttachmentId=attachment_id
        )
        assert response["TransitGatewayPeeringAttachment"]["State"] == "deleted"


def create_peering_attachment(
    ec2, gateway_id1, gateway_id2, peer_account=ACCOUNT_ID, peer_region="us-east-1"
):
    return ec2.create_transit_gateway_peering_attachment(
        TransitGatewayId=gateway_id1,
        PeerTransitGatewayId=gateway_id2,
        PeerAccountId=peer_account,
        PeerRegion=peer_region,
    )["TransitGatewayPeeringAttachment"]["TransitGatewayAttachmentId"]


def retrieve_all_attachments(client, filters=[]):  # pylint: disable=W0102
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
