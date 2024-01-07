from datetime import datetime
from unittest import SkipTest

import boto3
from freezegun import freeze_time

from moto import mock_aws, settings


@mock_aws
def test_rfc_returns_valid_date_for_every_possible_weekday_and_month():
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("Freezing time only possible in DecoratorMode")
    client = boto3.client("s3", region_name="us-east-1")
    client.create_bucket(Bucket="bucket_")
    for weekday in range(1, 8):
        with freeze_time(f"2023-02-{weekday} 12:00:00"):
            client.put_object(Bucket="bucket_", Key="test.txt", Body=b"test")
            obj = client.get_object(Bucket="bucket_", Key="test.txt")
            assert obj["LastModified"].replace(tzinfo=None) == datetime.now()
            # If we get here, the LastModified date will have been successfully parsed
            # Regardless of which weekday it is

    for month in range(1, 13):
        with freeze_time(f"2023-{month}-02 12:00:00"):
            client.put_object(Bucket="bucket_", Key="test.txt", Body=b"test")
            obj = client.get_object(Bucket="bucket_", Key="test.txt")
            assert obj["LastModified"].replace(tzinfo=None) == datetime.now()
            # If we get here, the LastModified date will have been successfully parsed
            # Regardless of which month it is
