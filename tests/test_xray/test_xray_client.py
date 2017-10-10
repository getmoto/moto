from __future__ import unicode_literals
from moto import mock_xray_client, XRaySegment, mock_dynamodb2
import sure   # noqa
import boto3

from aws_xray_sdk.core import patch_all

import botocore.client
import botocore.endpoint
original_make_api_call = botocore.client.BaseClient._make_api_call
original_encode_headers = botocore.endpoint.Endpoint._encode_headers


@mock_xray_client
@mock_dynamodb2
def test_xray_dynamo():
    patch_all()

    client = boto3.client('dynamodb', region_name='us-east-1')

    with XRaySegment():
        resp = client.list_tables()

    with XRaySegment():
        resp = client.list_tables()
        resp = client.list_tables()


    print()

    setattr(botocore.client.BaseClient, '_make_api_call', original_make_api_call)
    setattr(botocore.endpoint.Endpoint, '_encode_headers', original_encode_headers)