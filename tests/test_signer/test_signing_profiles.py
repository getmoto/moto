"""Unit tests for signer-supported APIs."""
import boto3

import sure  # noqa # pylint: disable=unused-import
from moto import mock_signer

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_signer
def test_put_signing_profile():
    client = boto3.client("signer", region_name="eu-west-1")
    resp = client.put_signing_profile(profileName="prof1", platformId="pid")

    resp.should.have.key("arn")
    resp.should.have.key("profileVersion")
    resp.should.have.key("profileVersionArn")


@mock_signer
def test_get_signing_profile():
    client = boto3.client("signer", region_name="eu-west-1")
    resp = client.put_signing_profile(
        profileName="prof1", platformId="AWSLambda-SHA384-ECDSA"
    )

    resp = client.get_signing_profile(profileName="prof1")

    resp.should.have.key("arn")
    resp.should.have.key("profileVersion")
    resp.should.have.key("profileVersionArn")
    resp.should.have.key("status").equals("Active")
    resp.should.have.key("profileName").equals("prof1")
    resp.should.have.key("platformId").equals("AWSLambda-SHA384-ECDSA")
    resp.should.have.key("signatureValidityPeriod").equals(
        {"type": "MONTHS", "value": 135}
    )


@mock_signer
def test_get_signing_profile__with_args():
    client = boto3.client("signer", region_name="eu-west-1")
    resp = client.put_signing_profile(
        profileName="prof1",
        platformId="AWSLambda-SHA384-ECDSA",
        signatureValidityPeriod={"type": "DAYS", "value": 10},
        tags={"k1": "v1", "k2": "v2"},
    )

    resp = client.get_signing_profile(profileName="prof1")

    resp.should.have.key("signatureValidityPeriod").equals(
        {"type": "DAYS", "value": 10}
    )
    resp.should.have.key("tags").equals({"k1": "v1", "k2": "v2"})


@mock_signer
def test_cancel_signing_profile():
    client = boto3.client("signer", region_name="eu-west-1")
    resp = client.put_signing_profile(
        profileName="prof1", platformId="AWSLambda-SHA384-ECDSA"
    )

    client.cancel_signing_profile(profileName="prof1")

    resp = client.get_signing_profile(profileName="prof1")

    resp.should.have.key("status").equals("Canceled")
