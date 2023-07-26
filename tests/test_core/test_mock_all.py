import boto3
import pytest

from moto import mock_all


@mock_all()
def test_decorator() -> None:
    rgn = "us-east-1"
    sqs = boto3.client("sqs", region_name=rgn)
    r = sqs.list_queues()
    assert r["ResponseMetadata"]["HTTPStatusCode"] == 200

    lmbda = boto3.client("lambda", region_name=rgn)
    r = lmbda.list_event_source_mappings()
    assert r["ResponseMetadata"]["HTTPStatusCode"] == 200

    ddb = boto3.client("dynamodb", region_name=rgn)
    r = ddb.list_tables()
    assert r["ResponseMetadata"]["HTTPStatusCode"] == 200


def test_context_manager() -> None:
    rgn = "us-east-1"

    with mock_all():
        sqs = boto3.client("sqs", region_name=rgn)
        r = sqs.list_queues()
        assert r["ResponseMetadata"]["HTTPStatusCode"] == 200

    unpatched_sqs = boto3.Session().client("sqs", region_name=rgn)

    with pytest.raises(Exception):
        unpatched_sqs.list_queues()
