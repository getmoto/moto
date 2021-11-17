import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import

from moto import mock_all


@mock_all()
def test_decorator():
    rgn = "us-east-1"
    sqs = boto3.client("sqs", region_name=rgn)
    r = sqs.list_queues()
    r["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    lmbda = boto3.client("lambda", region_name=rgn)
    r = lmbda.list_event_source_mappings()
    r["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    ddb = boto3.client("dynamodb", region_name=rgn)
    r = ddb.list_tables()
    r["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)


def test_context_manager():
    with mock_all():
        rgn = "us-east-1"
        sqs = boto3.client("sqs", region_name=rgn)
        r = sqs.list_queues()
        r["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

        lmbda = boto3.client("lambda", region_name=rgn)
        r = lmbda.list_event_source_mappings()
        r["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

        ddb = boto3.client("dynamodb", region_name=rgn)
        r = ddb.list_tables()
        r["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    with pytest.raises(Exception):
        sqs.list_queues()
