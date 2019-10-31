from __future__ import unicode_literals
import sure  # noqa
from nose.tools import assert_raises
import requests

import boto3
from moto import mock_sqs, settings

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

    res = requests.post("{base_url}/moto-api/reset".format(base_url=base_url))
    res.content.should.equal(b'{"status": "ok"}')

    conn.list_queues().shouldnt.contain("QueueUrls")  # No more queues


@mock_sqs
def test_data_api():
    conn = boto3.client("sqs", region_name="us-west-1")
    conn.create_queue(QueueName="queue1")

    res = requests.post("{base_url}/moto-api/data.json".format(base_url=base_url))
    queues = res.json()["sqs"]["Queue"]
    len(queues).should.equal(1)
    queue = queues[0]
    queue["name"].should.equal("queue1")
