from urllib.parse import urlencode

from moto import server


def test_create_queue_with_tags():
    backend = server.create_backend_app("sqs")
    queue_name = "test-queue"
    test_client = backend.test_client()
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
    }
    params = {
        "Action": "CreateQueue",
        "QueueName": queue_name,
        "Tag.1.Key": "foo",
        "Tag.1.Value": "bar",
    }
    resp = test_client.post(headers=headers, data=urlencode(params))
    assert resp.status_code == 200
    assert "<CreateQueueResult>" in resp.data.decode("utf-8")
    params = {
        "Action": "ListQueueTags",
        "QueueUrl": queue_name,
    }
    resp = test_client.post(headers=headers, data=urlencode(params))
    assert "<Tag><Key>foo</Key><Value>bar</Value></Tag>" in resp.data.decode("utf-8")
