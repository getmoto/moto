from __future__ import unicode_literals

import datetime

from botocore.exceptions import ClientError
import boto3
import sure  # noqa

from moto import mock_kinesis
from moto.core import ACCOUNT_ID


def create_s3_delivery_stream(client, stream_name):
    return client.create_delivery_stream(
        DeliveryStreamName=stream_name,
        DeliveryStreamType="DirectPut",
        ExtendedS3DestinationConfiguration={
            "RoleARN": "arn:aws:iam::{}:role/firehose_delivery_role".format(ACCOUNT_ID),
            "BucketARN": "arn:aws:s3:::kinesis-test",
            "Prefix": "myFolder/",
            "CompressionFormat": "UNCOMPRESSED",
            "DataFormatConversionConfiguration": {
                "Enabled": True,
                "InputFormatConfiguration": {"Deserializer": {"HiveJsonSerDe": {}}},
                "OutputFormatConfiguration": {
                    "Serializer": {"ParquetSerDe": {"Compression": "SNAPPY"}}
                },
                "SchemaConfiguration": {
                    "DatabaseName": stream_name,
                    "RoleARN": "arn:aws:iam::{}:role/firehose_delivery_role".format(
                        ACCOUNT_ID
                    ),
                    "TableName": "outputTable",
                },
            },
        },
    )


def create_redshift_delivery_stream(client, stream_name):
    return client.create_delivery_stream(
        DeliveryStreamName=stream_name,
        RedshiftDestinationConfiguration={
            "RoleARN": "arn:aws:iam::{}:role/firehose_delivery_role".format(ACCOUNT_ID),
            "ClusterJDBCURL": "jdbc:redshift://host.amazonaws.com:5439/database",
            "CopyCommand": {
                "DataTableName": "outputTable",
                "CopyOptions": "CSV DELIMITER ',' NULL '\\0'",
            },
            "Username": "username",
            "Password": "password",
            "S3Configuration": {
                "RoleARN": "arn:aws:iam::{}:role/firehose_delivery_role".format(
                    ACCOUNT_ID
                ),
                "BucketARN": "arn:aws:s3:::kinesis-test",
                "Prefix": "myFolder/",
                "BufferingHints": {"SizeInMBs": 123, "IntervalInSeconds": 124},
                "CompressionFormat": "UNCOMPRESSED",
            },
        },
    )


def create_elasticsearch_delivery_stream(client, stream_name):
    return client.create_delivery_stream(
        DeliveryStreamName=stream_name,
        DeliveryStreamType="DirectPut",
        ElasticsearchDestinationConfiguration={
            "RoleARN": "arn:aws:iam::{}:role/firehose_delivery_role".format(ACCOUNT_ID),
            "DomainARN": "arn:aws:es:::domain/kinesis-test",
            "IndexName": "myIndex",
            "TypeName": "UNCOMPRESSED",
            "IndexRotationPeriod": "NoRotation",
            "BufferingHints": {"IntervalInSeconds": 123, "SizeInMBs": 123},
            "RetryOptions": {"DurationInSeconds": 123},
            "S3Configuration": {
                "RoleARN": "arn:aws:iam::{}:role/firehose_delivery_role".format(
                    ACCOUNT_ID
                ),
                "BucketARN": "arn:aws:s3:::kinesis-test",
                "Prefix": "myFolder/",
                "BufferingHints": {"SizeInMBs": 123, "IntervalInSeconds": 124},
                "CompressionFormat": "UNCOMPRESSED",
            },
        },
    )


@mock_kinesis
def test_create_redshift_delivery_stream():
    client = boto3.client("firehose", region_name="us-east-1")

    response = create_redshift_delivery_stream(client, "stream1")
    stream_arn = response["DeliveryStreamARN"]

    response = client.describe_delivery_stream(DeliveryStreamName="stream1")
    stream_description = response["DeliveryStreamDescription"]

    # Sure and Freezegun don't play nicely together
    _ = stream_description.pop("CreateTimestamp")
    _ = stream_description.pop("LastUpdateTimestamp")

    stream_description.should.equal(
        {
            "DeliveryStreamName": "stream1",
            "DeliveryStreamARN": stream_arn,
            "DeliveryStreamStatus": "ACTIVE",
            "VersionId": "string",
            "Destinations": [
                {
                    "DestinationId": "string",
                    "RedshiftDestinationDescription": {
                        "RoleARN": "arn:aws:iam::{}:role/firehose_delivery_role".format(
                            ACCOUNT_ID
                        ),
                        "ClusterJDBCURL": "jdbc:redshift://host.amazonaws.com:5439/database",
                        "CopyCommand": {
                            "DataTableName": "outputTable",
                            "CopyOptions": "CSV DELIMITER ',' NULL '\\0'",
                        },
                        "Username": "username",
                        "S3DestinationDescription": {
                            "RoleARN": "arn:aws:iam::{}:role/firehose_delivery_role".format(
                                ACCOUNT_ID
                            ),
                            "BucketARN": "arn:aws:s3:::kinesis-test",
                            "Prefix": "myFolder/",
                            "BufferingHints": {
                                "SizeInMBs": 123,
                                "IntervalInSeconds": 124,
                            },
                            "CompressionFormat": "UNCOMPRESSED",
                        },
                    },
                }
            ],
            "HasMoreDestinations": False,
        }
    )


@mock_kinesis
def test_create_s3_delivery_stream():
    client = boto3.client("firehose", region_name="us-east-1")

    response = create_s3_delivery_stream(client, "stream1")
    stream_arn = response["DeliveryStreamARN"]

    response = client.describe_delivery_stream(DeliveryStreamName="stream1")
    stream_description = response["DeliveryStreamDescription"]

    # Sure and Freezegun don't play nicely together
    _ = stream_description.pop("CreateTimestamp")
    _ = stream_description.pop("LastUpdateTimestamp")

    stream_description.should.equal(
        {
            "DeliveryStreamName": "stream1",
            "DeliveryStreamARN": stream_arn,
            "DeliveryStreamStatus": "ACTIVE",
            "VersionId": "string",
            "Destinations": [
                {
                    "DestinationId": "string",
                    "ExtendedS3DestinationDescription": {
                        "RoleARN": "arn:aws:iam::{}:role/firehose_delivery_role".format(
                            ACCOUNT_ID
                        ),
                        "BucketARN": "arn:aws:s3:::kinesis-test",
                        "Prefix": "myFolder/",
                        "CompressionFormat": "UNCOMPRESSED",
                        "DataFormatConversionConfiguration": {
                            "Enabled": True,
                            "InputFormatConfiguration": {
                                "Deserializer": {"HiveJsonSerDe": {}}
                            },
                            "OutputFormatConfiguration": {
                                "Serializer": {
                                    "ParquetSerDe": {"Compression": "SNAPPY"}
                                }
                            },
                            "SchemaConfiguration": {
                                "DatabaseName": "stream1",
                                "RoleARN": "arn:aws:iam::{}:role/firehose_delivery_role".format(
                                    ACCOUNT_ID
                                ),
                                "TableName": "outputTable",
                            },
                        },
                    },
                }
            ],
            "HasMoreDestinations": False,
        }
    )


@mock_kinesis
def test_create_elasticsearch_delivery_stream():
    client = boto3.client("firehose", region_name="us-east-1")

    response = create_elasticsearch_delivery_stream(client, "stream1")
    stream_arn = response["DeliveryStreamARN"]

    response = client.describe_delivery_stream(DeliveryStreamName="stream1")
    stream_description = response["DeliveryStreamDescription"]

    # Sure and Freezegun don't play nicely together
    _ = stream_description.pop("CreateTimestamp")
    _ = stream_description.pop("LastUpdateTimestamp")

    stream_description.should.equal(
        {
            "DeliveryStreamName": "stream1",
            "DeliveryStreamARN": stream_arn,
            "DeliveryStreamStatus": "ACTIVE",
            "VersionId": "string",
            "Destinations": [
                {
                    "DestinationId": "string",
                    "ElasticsearchDestinationDescription": {
                        "RoleARN": "arn:aws:iam::{}:role/firehose_delivery_role".format(
                            ACCOUNT_ID
                        ),
                        "DomainARN": "arn:aws:es:::domain/kinesis-test",
                        "IndexName": "myIndex",
                        "TypeName": "UNCOMPRESSED",
                        "IndexRotationPeriod": "NoRotation",
                        "BufferingHints": {"IntervalInSeconds": 123, "SizeInMBs": 123},
                        "RetryOptions": {"DurationInSeconds": 123},
                        "S3DestinationDescription": {
                            "RoleARN": "arn:aws:iam::{}:role/firehose_delivery_role".format(
                                ACCOUNT_ID
                            ),
                            "BucketARN": "arn:aws:s3:::kinesis-test",
                            "Prefix": "myFolder/",
                            "BufferingHints": {
                                "SizeInMBs": 123,
                                "IntervalInSeconds": 124,
                            },
                            "CompressionFormat": "UNCOMPRESSED",
                        },
                    },
                }
            ],
            "HasMoreDestinations": False,
        }
    )


@mock_kinesis
def test_create_stream_without_redshift():
    client = boto3.client("firehose", region_name="us-east-1")

    response = client.create_delivery_stream(
        DeliveryStreamName="stream1",
        S3DestinationConfiguration={
            "RoleARN": "arn:aws:iam::{}:role/firehose_delivery_role".format(ACCOUNT_ID),
            "BucketARN": "arn:aws:s3:::kinesis-test",
            "Prefix": "myFolder/",
            "BufferingHints": {"SizeInMBs": 123, "IntervalInSeconds": 124},
            "CompressionFormat": "UNCOMPRESSED",
        },
    )
    stream_arn = response["DeliveryStreamARN"]

    response = client.describe_delivery_stream(DeliveryStreamName="stream1")
    stream_description = response["DeliveryStreamDescription"]

    # Sure and Freezegun don't play nicely together
    _ = stream_description.pop("CreateTimestamp")
    _ = stream_description.pop("LastUpdateTimestamp")

    stream_description.should.equal(
        {
            "DeliveryStreamName": "stream1",
            "DeliveryStreamARN": stream_arn,
            "DeliveryStreamStatus": "ACTIVE",
            "VersionId": "string",
            "Destinations": [
                {
                    "DestinationId": "string",
                    "S3DestinationDescription": {
                        "RoleARN": "arn:aws:iam::{}:role/firehose_delivery_role".format(
                            ACCOUNT_ID
                        ),
                        "RoleARN": "arn:aws:iam::{}:role/firehose_delivery_role".format(
                            ACCOUNT_ID
                        ),
                        "BucketARN": "arn:aws:s3:::kinesis-test",
                        "Prefix": "myFolder/",
                        "BufferingHints": {"SizeInMBs": 123, "IntervalInSeconds": 124},
                        "CompressionFormat": "UNCOMPRESSED",
                    },
                }
            ],
            "HasMoreDestinations": False,
        }
    )


@mock_kinesis
def test_deescribe_non_existent_stream():
    client = boto3.client("firehose", region_name="us-east-1")

    client.describe_delivery_stream.when.called_with(
        DeliveryStreamName="not-a-stream"
    ).should.throw(ClientError)


@mock_kinesis
def test_list_and_delete_stream():
    client = boto3.client("firehose", region_name="us-east-1")

    create_redshift_delivery_stream(client, "stream1")
    create_redshift_delivery_stream(client, "stream2")

    set(client.list_delivery_streams()["DeliveryStreamNames"]).should.equal(
        set(["stream1", "stream2"])
    )

    client.delete_delivery_stream(DeliveryStreamName="stream1")

    set(client.list_delivery_streams()["DeliveryStreamNames"]).should.equal(
        set(["stream2"])
    )


@mock_kinesis
def test_put_record():
    client = boto3.client("firehose", region_name="us-east-1")

    create_redshift_delivery_stream(client, "stream1")
    client.put_record(DeliveryStreamName="stream1", Record={"Data": "some data"})


@mock_kinesis
def test_put_record_batch():
    client = boto3.client("firehose", region_name="us-east-1")

    create_redshift_delivery_stream(client, "stream1")
    client.put_record_batch(
        DeliveryStreamName="stream1",
        Records=[{"Data": "some data1"}, {"Data": "some data2"}],
    )
