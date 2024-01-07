import json
from unittest import SkipTest, TestCase

import boto3
import pytest
import requests
from botocore.exceptions import ClientError

from moto import mock_aws, settings
from moto.core.model_instances import model_data, reset_model_data

base_url = (
    "http://localhost:5000"
    if settings.TEST_SERVER_MODE
    else "http://motoapi.amazonaws.com"
)
data_url = f"{base_url}/moto-api/data.json"


@mock_aws
def test_reset_api() -> None:
    conn = boto3.client("sqs", region_name="us-west-1")
    conn.create_queue(QueueName="queue1")
    assert len(conn.list_queues()["QueueUrls"]) == 1

    res = requests.post(f"{base_url}/moto-api/reset")
    assert res.content == b'{"status": "ok"}'

    assert "QueueUrls" not in conn.list_queues()  # No more queues


@mock_aws
def test_data_api() -> None:
    conn = boto3.client("sqs", region_name="us-west-1")
    conn.create_queue(QueueName="queue1")

    queues = requests.post(data_url).json()["sqs"]["Queue"]
    assert len(queues) == 1
    queue = queues[0]
    assert queue["name"] == "queue1"


@mock_aws
def test_overwriting_s3_object_still_returns_data() -> None:
    if settings.TEST_SERVER_MODE:
        raise SkipTest("No point in testing this behaves the same in ServerMode")
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket="test")
    s3.put_object(Bucket="test", Body=b"t", Key="file.txt")
    assert len(requests.post(data_url).json()["s3"]["FakeKey"]) == 1
    s3.put_object(Bucket="test", Body=b"t", Key="file.txt")
    assert len(requests.post(data_url).json()["s3"]["FakeKey"]) == 2


@mock_aws
def test_creation_error__data_api_still_returns_thing() -> None:
    if settings.TEST_SERVER_MODE:
        raise SkipTest("No point in testing this behaves the same in ServerMode")
    # Timeline:
    #
    # When calling BaseModel.__new__, the created instance (of type FakeAutoScalingGroup) is stored in `model_data`
    # We then try and initialize the instance by calling __init__
    #
    # Initialization fails in this test, but: by then, the instance is already registered
    # This test ensures that we can still print/__repr__ the uninitialized instance, despite the fact that no attributes have been set
    client = boto3.client("autoscaling", region_name="us-east-1")
    # Creating this ASG fails, because it doesn't specify a Region/VPC
    with pytest.raises(ClientError):
        client.create_auto_scaling_group(
            AutoScalingGroupName="test_asg",
            LaunchTemplate={
                "LaunchTemplateName": "test_launch_template",
                "Version": "1",
            },
            MinSize=0,
            MaxSize=20,
        )

    from moto.moto_api._internal.urls import response_instance

    _, _, x = response_instance.model_data(None, "None", None)

    as_objects = json.loads(x)["autoscaling"]
    assert len(as_objects["FakeAutoScalingGroup"]) >= 1

    names = [obj["name"] for obj in as_objects["FakeAutoScalingGroup"]]
    assert "test_asg" in names


def test_model_data_is_emptied_as_necessary() -> None:
    if settings.TEST_SERVER_MODE:
        raise SkipTest("We're only interested in the decorator performance here")

    # Reset any residual data
    reset_model_data()

    # No instances exist, because we have just reset it
    for classes_per_service in model_data.values():
        for _class in classes_per_service.values():
            assert _class.instances == []  # type: ignore[attr-defined]

    # TODO: ensure that iam is not loaded, and IAM policies are not created
    # with mock_aws(load_static_data=False) ?
    with mock_aws():
        # When just starting a mock, it is empty
        for classes_per_service in model_data.values():
            for _class in classes_per_service.values():
                assert _class.instances == []  # type: ignore[attr-defined]

        # After creating a queue, some data will be present
        conn = boto3.client("sqs", region_name="us-west-1")
        conn.create_queue(QueueName="queue1")

        assert len(model_data["sqs"]["Queue"].instances) == 1  # type: ignore[attr-defined]

    # But after the mock ends, it is empty again
    for classes_per_service in model_data.values():
        for _class in classes_per_service.values():
            assert _class.instances == []  # type: ignore[attr-defined]

    # When we have multiple/nested mocks, the data should still be present after the first mock ends
    with mock_aws():
        conn = boto3.client("sqs", region_name="us-west-1")
        conn.create_queue(QueueName="queue1")
        with mock_aws():
            # The data should still be here - instances should not reset if another mock is still active
            assert len(model_data["sqs"]["Queue"].instances) == 1  # type: ignore[attr-defined]
        # The data should still be here - the inner mock has exited, but the outer mock is still active
        assert len(model_data["sqs"]["Queue"].instances) == 1  # type: ignore[attr-defined]


@mock_aws
class TestModelDataResetForClassDecorator(TestCase):
    def setUp(self) -> None:
        if settings.TEST_SERVER_MODE:
            raise SkipTest("We're only interested in the decorator performance here")

        # No data is present at the beginning
        for classes_per_service in model_data.values():
            for _class in classes_per_service.values():
                assert _class.instances == []  # type: ignore[attr-defined]

        conn = boto3.client("sqs", region_name="us-west-1")
        conn.create_queue(QueueName="queue1")

    def test_should_find_bucket(self) -> None:
        assert len(model_data["sqs"]["Queue"].instances) == 1  # type: ignore[attr-defined]
