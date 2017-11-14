from __future__ import unicode_literals

import sure  # noqa

import moto.server as server

'''
Test the different server responses
'''


def test_sns_server_get():
    backend = server.create_backend_app("sns")
    test_client = backend.test_client()

    topic_data = test_client.action_data("CreateTopic", Name="testtopic")
    topic_data.should.contain("CreateTopicResult")
    topic_data.should.contain(
        "<TopicArn>arn:aws:sns:us-east-1:123456789012:testtopic</TopicArn>")

    topics_data = test_client.action_data("ListTopics")
    topics_data.should.contain("ListTopicsResult")
    topic_data.should.contain(
        "<TopicArn>arn:aws:sns:us-east-1:123456789012:testtopic</TopicArn>")
