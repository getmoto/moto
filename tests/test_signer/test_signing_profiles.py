import boto3

from moto import mock_aws

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
def test_put_signing_profile():
    client = boto3.client("signer", region_name="eu-west-1")
    resp = client.put_signing_profile(profileName="prof1", platformId="pid")

    assert "arn" in resp
    assert "profileVersion" in resp
    assert "profileVersionArn" in resp


@mock_aws
def test_get_signing_profile():
    client = boto3.client("signer", region_name="eu-west-1")
    client.put_signing_profile(profileName="prof1", platformId="AWSLambda-SHA384-ECDSA")

    resp = client.get_signing_profile(profileName="prof1")

    assert "arn" in resp
    assert "profileVersion" in resp
    assert "profileVersionArn" in resp
    assert resp["status"] == "Active"
    assert resp["profileName"] == "prof1"
    assert resp["platformId"] == "AWSLambda-SHA384-ECDSA"
    assert resp["signatureValidityPeriod"] == {"type": "MONTHS", "value": 135}


@mock_aws
def test_get_signing_profile__with_args():
    client = boto3.client("signer", region_name="eu-west-1")
    profile_arn = client.put_signing_profile(
        profileName="prof1",
        platformId="AWSLambda-SHA384-ECDSA",
        signatureValidityPeriod={"type": "DAYS", "value": 10},
        signingMaterial={"certificateArn": "some arn"},
        tags={"k1": "v1", "k2": "v2"},
    )["arn"]

    resp = client.get_signing_profile(profileName="prof1")

    assert resp["signatureValidityPeriod"] == {"type": "DAYS", "value": 10}
    assert resp["tags"] == {"k1": "v1", "k2": "v2"}
    assert resp["signingMaterial"] == {"certificateArn": "some arn"}

    tag_list = client.list_tags_for_resource(resourceArn=profile_arn)["tags"]
    assert tag_list == {"k1": "v1", "k2": "v2"}

    client.tag_resource(resourceArn=profile_arn, tags={"k3": "v3"})

    tag_list = client.list_tags_for_resource(resourceArn=profile_arn)["tags"]
    assert tag_list == {"k1": "v1", "k2": "v2", "k3": "v3"}

    client.untag_resource(resourceArn=profile_arn, tagKeys=["k2"])

    tag_list = client.list_tags_for_resource(resourceArn=profile_arn)["tags"]
    assert tag_list == {"k1": "v1", "k3": "v3"}


@mock_aws
def test_cancel_signing_profile():
    client = boto3.client("signer", region_name="eu-west-1")
    client.put_signing_profile(profileName="prof1", platformId="AWSLambda-SHA384-ECDSA")

    client.cancel_signing_profile(profileName="prof1")

    resp = client.get_signing_profile(profileName="prof1")

    assert resp["status"] == "Canceled"
