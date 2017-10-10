from __future__ import unicode_literals
from moto import mock_xray_client, XRaySegment, mock_dynamodb2
import sure   # noqa
import boto3

from aws_xray_sdk.core import patch_all

# Simulate that an imported module will already have ran this
patch_all()


@mock_xray_client
@mock_dynamodb2
def test_xray_dynamo():

    client = boto3.client('dynamodb')

    with XRaySegment():
        resp = client.list_tables()

    with XRaySegment():
        resp = client.list_tables()
        resp = client.list_tables()


    print()