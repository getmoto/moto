"""Unit tests for signer-supported APIs."""
import boto3

from moto import mock_signer

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_signer
def test_list_signing_platforms():
    client = boto3.client("signer", region_name="us-east-2")
    resp = client.list_signing_platforms()

    assert "platforms" in resp
    assert len(resp["platforms"]) == 4

    partners = [x["partner"] for x in resp["platforms"]]
    assert set(partners) == {"AmazonFreeRTOS", "AWSLambda", "AWSIoTDeviceManagement"}
