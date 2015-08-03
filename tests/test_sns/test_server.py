from __future__ import unicode_literals

import json

import re
import sure  # noqa

import moto.server as server

'''
Test the different server responses
'''


def test_sns_server_get():
    backend = server.create_backend_app("sns")
    test_client = backend.test_client()

    topic_data = test_client.action_json("CreateTopic", Name="test topic")
    topic_arn = topic_data["CreateTopicResponse"]["CreateTopicResult"]["TopicArn"]
    topics_data = test_client.action_json("ListTopics")
    topics_arns = [t["TopicArn"] for t in topics_data["ListTopicsResponse"]["ListTopicsResult"]["Topics"]]

    assert topic_arn in topics_arns