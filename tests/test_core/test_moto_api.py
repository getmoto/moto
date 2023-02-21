import sure  # noqa # pylint: disable=unused-import
import requests

import boto3
import json
import pytest
from botocore.exceptions import ClientError
from moto import mock_autoscaling, mock_s3, mock_sqs, settings
from moto.core.model_instances import model_data, reset_model_data
from unittest import SkipTest, TestCase

base_url = (
    "http://localhost:5000"
    if settings.TEST_SERVER_MODE
    else "http://motoapi.amazonaws.com"
)


@mock_sqs
def test_reset_api():
    conn = boto3.client("sqs", region_name="us-west-1")
    conn.create_queue(QueueName="queue1")
    conn.list_queues()["QueueUrls"].should.have.length_of(1)

    res = requests.post(f"{base_url}/moto-api/reset")
    res.content.should.equal(b'{"status": "ok"}')

    conn.list_queues().shouldnt.contain("QueueUrls")  # No more queues


@mock_sqs
def test_data_api():
    conn = boto3.client("sqs", region_name="us-west-1")
    conn.create_queue(QueueName="queue1")

    res = requests.post(f"{base_url}/moto-api/data.json")
    queues = res.json()["sqs"]["Queue"]
    len(queues).should.equal(1)
    queue = queues[0]
    queue["name"].should.equal("queue1")


@mock_autoscaling
def test_creation_error__data_api_still_returns_thing():
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

    _, _, x = response_instance.model_data(None, None, None)

    as_objects = json.loads(x)["autoscaling"]
    as_objects.should.have.key("FakeAutoScalingGroup")
    assert len(as_objects["FakeAutoScalingGroup"]) >= 1

    names = [obj["name"] for obj in as_objects["FakeAutoScalingGroup"]]
    names.should.contain("test_asg")


def test_model_data_is_emptied_as_necessary():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("We're only interested in the decorator performance here")

    # Reset any residual data
    reset_model_data()

    # No instances exist, because we have just reset it
    for classes_per_service in model_data.values():
        for _class in classes_per_service.values():
            _class.instances.should.equal([])

    with mock_sqs():
        # When just starting a mock, it is empty
        for classes_per_service in model_data.values():
            for _class in classes_per_service.values():
                _class.instances.should.equal([])

        # After creating a queue, some data will be present
        conn = boto3.client("sqs", region_name="us-west-1")
        conn.create_queue(QueueName="queue1")

        model_data["sqs"]["Queue"].instances.should.have.length_of(1)

    # But after the mock ends, it is empty again
    for classes_per_service in model_data.values():
        for _class in classes_per_service.values():
            _class.instances.should.equal([])

    # When we have multiple/nested mocks, the data should still be present after the first mock ends
    with mock_sqs():
        conn = boto3.client("sqs", region_name="us-west-1")
        conn.create_queue(QueueName="queue1")
        with mock_s3():
            # The data should still be here - instances should not reset if another mock is still active
            model_data["sqs"]["Queue"].instances.should.have.length_of(1)
        # The data should still be here - the inner mock has exited, but the outer mock is still active
        model_data["sqs"]["Queue"].instances.should.have.length_of(1)


@mock_sqs
class TestModelDataResetForClassDecorator(TestCase):
    def setUp(self):
        if settings.TEST_SERVER_MODE:
            raise SkipTest("We're only interested in the decorator performance here")

        # No data is present at the beginning
        for classes_per_service in model_data.values():
            for _class in classes_per_service.values():
                _class.instances.should.equal([])

        conn = boto3.client("sqs", region_name="us-west-1")
        conn.create_queue(QueueName="queue1")

    def test_should_find_bucket(self):
        model_data["sqs"]["Queue"].instances.should.have.length_of(1)
