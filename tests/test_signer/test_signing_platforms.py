"""Unit tests for signer-supported APIs."""
import boto3

import sure  # noqa # pylint: disable=unused-import
from moto import mock_signer

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_signer
def test_list_signing_platforms():
    client = boto3.client("signer", region_name="us-east-2")
    resp = client.list_signing_platforms()

    resp.should.have.key("platforms").should.have.length_of(4)

    partners = [x["partner"] for x in resp["platforms"]]
    set(partners).should.equal(
        {"AmazonFreeRTOS", "AWSLambda", "AWSIoTDeviceManagement"}
    )
