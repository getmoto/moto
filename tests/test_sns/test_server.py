import moto.server as server
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID


def test_sns_server_get():
    backend = server.create_backend_app("sns")
    test_client = backend.test_client()

    topic_data = test_client.action_data("CreateTopic", Name="testtopic")
    assert "CreateTopicResult" in topic_data
    assert (
        f"<TopicArn>arn:aws:sns:us-east-1:{ACCOUNT_ID}:testtopic</TopicArn>"
    ) in topic_data

    topics_data = test_client.action_data("ListTopics")
    assert "ListTopicsResult" in topics_data
    assert (
        f"<TopicArn>arn:aws:sns:us-east-1:{ACCOUNT_ID}:testtopic</TopicArn>"
    ) in topics_data
