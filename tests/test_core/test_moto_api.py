import sure  # noqa # pylint: disable=unused-import
import requests

import boto3
import json
import pytest
from botocore.exceptions import ClientError
from moto import mock_autoscaling, mock_sqs, settings
from unittest import SkipTest

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
