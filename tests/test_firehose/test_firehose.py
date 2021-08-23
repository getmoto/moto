"""Unit tests specific to the Firehose Delivery Stream-related APIs.

 These APIs include:
   create_delivery_stream
   describe_delivery_stream
   delete_delivery_stream
   list_delivery_streams
"""
from io import BytesIO
import boto3

from moto import mock_firehose

TEST_REGION = "us-east-1" if settings.TEST_SERVER_MODE else "us-west-2"

@mock_firehose
def test_create_delivery_stream():
    pass

@mock_firehose
def test_delete_delivery_stream():
    pass

@mock_firehose
def test_describe_delivery_stream():
    pass

@mock_firehose
def test_list_delivery_streams():
    pass
