"""Unit tests for emrserverless-supported APIs."""
import boto3

import sure  # noqa # pylint: disable=unused-import
from moto import mock_emrserverless

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_emrserverless
def test_create_application():
    client = boto3.client("emr-serverless", region_name="us-east-1")
    resp = client.create_application(
        name="test-emr-serverless", type="SPARK", releaseLabel="emr-6.5.0-preview"
    )

    assert resp['name'] == "test-emr-serverless"


@mock_emrserverless
def test_list_applications():
    client = boto3.client("emr-serverless", region_name="us-east-1")
    # TODO: Move this to a fixture
    client.create_application(
        name="test-emr-serverless", type="SPARK", releaseLabel="emr-6.5.0-preview"
    )
    resp = client.list_applications()
    assert len(resp['applications']) == 1
