import hashlib
import json
import os
import re
import sys
import time
from unittest import SkipTest, mock
from uuid import uuid4

import boto3
import botocore.exceptions
import pytest
from botocore.exceptions import ClientError
from freezegun import freeze_time

from moto import mock_aws, settings
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from moto.sqs.models import (
    MAXIMUM_MESSAGE_LENGTH,
    MAXIMUM_MESSAGE_SIZE_ATTR_LOWER_BOUND,
    MAXIMUM_MESSAGE_SIZE_ATTR_UPPER_BOUND,
    Queue,
)
from moto.utilities.distutils_version import LooseVersion

from . import sqs_aws_verified

TEST_POLICY = """
{
  "Version":"2012-10-17",
  "Statement":[
    {
      "Effect": "Allow",
      "Principal": { "AWS": "*" },
      "Action": "sqs:SendMessage",
      "Resource": "'$sqs_queue_arn'",
      "Condition":{
        "ArnEquals":{
        "aws:SourceArn":"'$sns_topic_arn'"
        }
      }
    }
  ]
}
"""

MOCK_DEDUPLICATION_TIME_IN_SECONDS = 5
REGION = "us-east-1"


@mock_aws
def test_create_fifo_queue_fail():
    sqs = boto3.client("sqs", region_name=REGION)

    try:
        sqs.create_queue(QueueName=str(uuid4())[0:6], Attributes={"FifoQueue": "true"})
    except botocore.exceptions.ClientError as err:
        assert err.response["Error"]["Code"] == "InvalidParameterValue"
    else:
        raise RuntimeError("Should have raised InvalidParameterValue Exception")


@mock_aws
@pytest.mark.parametrize(
    "queue_name",
    [
        "",
        "ppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppp",
        "/my/test",
        "!@£$%^&*()queue",
    ],
)
def test_create_fifo_queue_invalid_name(queue_name):
    sqs = boto3.client("sqs", region_name=REGION)

    with pytest.raises(ClientError) as ex:
        sqs.create_queue(QueueName=queue_name)

    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert (
        err["Message"]
        == "Can only include alphanumeric characters, hyphens, or underscores. 1 to 80 in length"
    )


@mock_aws
def test_create_queue_with_same_attributes():
    sqs = boto3.client("sqs", region_name=REGION)

    dlq_url = sqs.create_queue(QueueName=str(uuid4()))["QueueUrl"]
    dlq_arn = sqs.get_queue_attributes(QueueUrl=dlq_url, AttributeNames=["All"])[
        "Attributes"
    ]["QueueArn"]

    attributes = {
        "DelaySeconds": "900",
        "MaximumMessageSize": "262144",
        "MessageRetentionPeriod": "1209600",
        "ReceiveMessageWaitTimeSeconds": "20",
        "RedrivePolicy": json.dumps(
            {"deadLetterTargetArn": dlq_arn, "maxReceiveCount": 100}
        ),
        "VisibilityTimeout": "43200",
    }

    q_name = str(uuid4())[0:6]
    sqs.create_queue(QueueName=q_name, Attributes=attributes)

    sqs.create_queue(QueueName=q_name, Attributes=attributes)


@mock_aws
def test_create_queue_with_different_attributes_fail():
    sqs = boto3.client("sqs", region_name=REGION)

    q_name = str(uuid4())[0:6]
    sqs.create_queue(QueueName=q_name, Attributes={"VisibilityTimeout": "10"})
    try:
        sqs.create_queue(QueueName=q_name, Attributes={"VisibilityTimeout": "60"})
    except botocore.exceptions.ClientError as err:
        assert err.response["Error"]["Code"] == "QueueAlreadyExists"
    else:
        raise RuntimeError("Should have raised QueueAlreadyExists Exception")

    q_name2 = str(uuid4())[0:6]
    response = sqs.create_queue(QueueName=q_name2, Attributes={"FifoQueue": "tru"})

    attributes = {"VisibilityTimeout": "60"}
    sqs.set_queue_attributes(QueueUrl=response.get("QueueUrl"), Attributes=attributes)

    new_response = sqs.create_queue(QueueName=q_name2, Attributes={"FifoQueue": "tru"})
    assert new_response["QueueUrl"] == response.get("QueueUrl")


@mock_aws
def test_create_fifo_queue():
    # given
    sqs = boto3.client("sqs", region_name=REGION)
    queue_name = f"{str(uuid4())[0:6]}.fifo"

    # when
    queue_url = sqs.create_queue(
        QueueName=queue_name, Attributes={"FifoQueue": "true"}
    )["QueueUrl"]

    # then
    assert queue_name in queue_url

    attributes = sqs.get_queue_attributes(QueueUrl=queue_url, AttributeNames=["All"])[
        "Attributes"
    ]
    assert attributes["ApproximateNumberOfMessages"] == "0"
    assert attributes["ApproximateNumberOfMessagesNotVisible"] == "0"
    assert attributes["ApproximateNumberOfMessagesDelayed"] == "0"
    assert isinstance(attributes["CreatedTimestamp"], str)
    assert attributes["ContentBasedDeduplication"] == "false"
    assert attributes["DeduplicationScope"] == "queue"
    assert attributes["DelaySeconds"] == "0"
    assert isinstance(attributes["LastModifiedTimestamp"], str)
    assert attributes["FifoQueue"] == "true"
    assert attributes["FifoThroughputLimit"] == "perQueue"
    assert attributes["MaximumMessageSize"] == "262144"
    assert attributes["MessageRetentionPeriod"] == "345600"
    assert attributes["QueueArn"] == (f"arn:aws:sqs:{REGION}:{ACCOUNT_ID}:{queue_name}")
    assert attributes["ReceiveMessageWaitTimeSeconds"] == "0"
    assert attributes["VisibilityTimeout"] == "30"


@mock_aws
def test_create_fifo_queue_with_high_throughput():
    # given
    sqs = boto3.client("sqs", region_name=REGION)
    queue_name = f"{str(uuid4())[0:6]}.fifo"

    # when
    queue_url = sqs.create_queue(
        QueueName=queue_name,
        Attributes={
            "FifoQueue": "true",
            "DeduplicationScope": "messageGroup",
            "FifoThroughputLimit": "perMessageGroupId",
        },
    )["QueueUrl"]

    # then
    assert queue_name in queue_url

    attributes = sqs.get_queue_attributes(QueueUrl=queue_url, AttributeNames=["All"])[
        "Attributes"
    ]
    assert attributes["DeduplicationScope"] == "messageGroup"
    assert attributes["FifoQueue"] == "true"
    assert attributes["FifoThroughputLimit"] == "perMessageGroupId"


@mock_aws
@pytest.mark.parametrize(
    "q_name",
    [
        str(uuid4())[0:6],
        "name_with_underscores",
        "name-with-hyphens",
        "Name-with_all_the_THings",
    ],
    ids=["random", "underscores", "hyphens", "combined"],
)
def test_create_queue(q_name):
    sqs = boto3.resource("sqs", region_name=REGION)

    new_queue = sqs.create_queue(QueueName=q_name)
    assert q_name in getattr(new_queue, "url")

    queue = sqs.get_queue_by_name(QueueName=q_name)
    assert queue.attributes.get("QueueArn").split(":")[-1] == q_name
    assert queue.attributes.get("QueueArn").split(":")[3] == REGION
    assert queue.attributes.get("VisibilityTimeout") == "30"


@mock_aws
def test_create_queue_kms():
    sqs = boto3.resource("sqs", region_name=REGION)

    q_name = str(uuid4())[0:6]
    sqs.create_queue(
        QueueName=q_name,
        Attributes={
            "KmsMasterKeyId": "master-key-id",
            "KmsDataKeyReusePeriodSeconds": "600",
        },
    )

    queue = sqs.get_queue_by_name(QueueName=q_name)

    assert queue.attributes.get("KmsMasterKeyId") == "master-key-id"
    assert queue.attributes.get("KmsDataKeyReusePeriodSeconds") == "600"


@mock_aws
def test_create_queue_with_tags():
    client = boto3.client("sqs", region_name=REGION)
    q_name = str(uuid4())[0:6]
    response = client.create_queue(
        QueueName=q_name, tags={"tag_key_1": "tag_value_1", "tag_key_2": ""}
    )
    queue_url = response["QueueUrl"]

    assert client.list_queue_tags(QueueUrl=queue_url)["Tags"] == {
        "tag_key_1": "tag_value_1",
        "tag_key_2": "",
    }


@mock_aws
def test_create_queue_with_policy():
    client = boto3.client("sqs", region_name=REGION)
    q_name = str(uuid4())[0:6]
    response = client.create_queue(
        QueueName=q_name,
        Attributes={
            "Policy": json.dumps(
                {
                    "Version": "2012-10-17",
                    "Id": "test",
                    "Statement": [{"Effect": "Allow", "Principal": "*", "Action": "*"}],
                }
            )
        },
    )
    queue_url = response["QueueUrl"]

    response = client.get_queue_attributes(
        QueueUrl=queue_url, AttributeNames=["Policy"]
    )
    assert json.loads(response["Attributes"]["Policy"]) == {
        "Version": "2012-10-17",
        "Id": "test",
        "Statement": [{"Effect": "Allow", "Principal": "*", "Action": "*"}],
    }


@mock_aws
def test_set_queue_attribute_empty_policy_removes_attr():
    client = boto3.client("sqs", region_name=REGION)
    q_name = str(uuid4())[0:6]
    response = client.create_queue(
        QueueName=q_name,
        Attributes={
            "Policy": json.dumps(
                {
                    "Version": "2012-10-17",
                    "Id": "test",
                    "Statement": [{"Effect": "Allow", "Principal": "*", "Action": "*"}],
                }
            )
        },
    )
    queue_url = response["QueueUrl"]

    empty_policy = {"Policy": ""}
    client.set_queue_attributes(QueueUrl=queue_url, Attributes=empty_policy)
    response = client.get_queue_attributes(QueueUrl=queue_url, AttributeNames=["All"])[
        "Attributes"
    ]
    assert "Policy" not in response


def test_is_empty_redrive_policy_returns_true_for_empty_and_falsy_values():
    assert Queue._is_empty_redrive_policy("")
    assert Queue._is_empty_redrive_policy("{}")


def test_is_empty_redrive_policy_returns_false_for_valid_policy_format():
    test_dlq_arn = f"arn:aws:sqs:{REGION}:123456789012:test-dlr-queue"
    assert not Queue._is_empty_redrive_policy(
        json.dumps({"deadLetterTargetArn": test_dlq_arn, "maxReceiveCount": 5})
    )
    assert not Queue._is_empty_redrive_policy(json.dumps({"maxReceiveCount": 5}))


@mock_aws
def test_set_queue_attribute_empty_redrive_removes_attr():
    client = boto3.client("sqs", region_name=REGION)

    dlq_resp = client.create_queue(QueueName="test-dlr-queue")
    dlq_arn1 = client.get_queue_attributes(
        QueueUrl=dlq_resp["QueueUrl"], AttributeNames=["QueueArn"]
    )["Attributes"]["QueueArn"]
    q_name = str(uuid4())[0:6]
    response = client.create_queue(
        QueueName=q_name,
        Attributes={
            "RedrivePolicy": json.dumps(
                {"deadLetterTargetArn": dlq_arn1, "maxReceiveCount": 5}
            ),
        },
    )
    queue_url = response["QueueUrl"]

    no_redrive = {"RedrivePolicy": ""}
    client.set_queue_attributes(QueueUrl=queue_url, Attributes=no_redrive)
    response = client.get_queue_attributes(QueueUrl=queue_url, AttributeNames=["All"])[
        "Attributes"
    ]
    assert "RedrivePolicy" not in response


@mock_aws
def test_get_queue_url():
    client = boto3.client("sqs", region_name=REGION)
    q_name = str(uuid4())[0:6]
    client.create_queue(QueueName=q_name)

    response = client.get_queue_url(QueueName=q_name)

    assert q_name in response["QueueUrl"]


@mock_aws
def test_get_queue_url_error_not_exists():
    # given
    client = boto3.client("sqs", region_name=REGION)

    # when
    with pytest.raises(ClientError) as e:
        client.get_queue_url(QueueName="not-exists")

    # then
    ex = e.value
    assert ex.operation_name == "GetQueueUrl"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "AWS.SimpleQueueService.NonExistentQueue" in ex.response["Error"]["Code"]
    assert ex.response["Error"]["Message"] == (
        "The specified queue does not exist for this wsdl version."
    )


@mock_aws
def test_get_nonexistent_queue():
    sqs = boto3.resource("sqs", region_name=REGION)

    with pytest.raises(ClientError) as err:
        sqs.Queue("http://whatever-incorrect-queue-address").load()
    ex = err.value
    assert ex.operation_name == "GetQueueAttributes"
    assert ex.response["Error"]["Code"] == "AWS.SimpleQueueService.NonExistentQueue"
    assert ex.response["Error"]["Message"] == (
        "The specified queue does not exist for this wsdl version."
    )


@mock_aws
def test_message_send_without_attributes():
    sqs = boto3.resource("sqs", region_name=REGION)
    queue = sqs.create_queue(QueueName=str(uuid4())[0:6])
    msg = queue.send_message(MessageBody="derp")
    assert msg.get("MD5OfMessageBody") == "58fd9edd83341c29f1aebba81c31e257"
    assert "MD5OfMessageAttributes" not in msg
    assert " \n" not in msg.get("MessageId")

    messages = queue.receive_messages()
    assert len(messages) == 1


@mock_aws
def test_message_send_with_attributes():
    sqs = boto3.resource("sqs", region_name=REGION)
    queue = sqs.create_queue(QueueName=str(uuid4())[0:6])
    msg = queue.send_message(
        MessageBody="derp",
        MessageAttributes={
            "SOME_Valid.attribute-Name": {
                "StringValue": "1493147359900",
                "DataType": "Number",
            }
        },
    )
    assert msg.get("MD5OfMessageBody") == "58fd9edd83341c29f1aebba81c31e257"
    assert msg.get("MD5OfMessageAttributes") == "36655e7e9d7c0e8479fa3f3f42247ae7"
    assert " \n" not in msg.get("MessageId")

    messages = queue.receive_messages()
    assert len(messages) == 1


@mock_aws
def test_message_retention_period():
    sqs = boto3.resource("sqs", region_name=REGION)
    queue = sqs.create_queue(
        QueueName=str(uuid4())[0:6], Attributes={"MessageRetentionPeriod": "3"}
    )
    queue.send_message(
        MessageBody="derp",
        MessageAttributes={
            "SOME_Valid.attribute-Name": {
                "StringValue": "1493147359900",
                "DataType": "Number",
            }
        },
    )

    messages = queue.receive_messages()
    assert len(messages) == 1

    queue.send_message(
        MessageBody="derp",
        MessageAttributes={
            "SOME_Valid.attribute-Name": {
                "StringValue": "1493147359900",
                "DataType": "Number",
            }
        },
    )

    time.sleep(5)
    messages = queue.receive_messages()
    assert len(messages) == 0


@mock_aws
def test_queue_retention_period():
    sqs = boto3.resource("sqs", region_name=REGION)
    queue = sqs.create_queue(
        QueueName=str(uuid4())[0:6], Attributes={"MessageRetentionPeriod": "3"}
    )

    time.sleep(5)

    queue.send_message(
        MessageBody="derp",
        MessageAttributes={
            "SOME_Valid.attribute-Name": {
                "StringValue": "1493147359900",
                "DataType": "Number",
            }
        },
    )

    messages = queue.receive_messages()
    assert len(messages) == 1


@mock_aws
def test_message_with_invalid_attributes():
    sqs = boto3.resource("sqs", region_name=REGION)
    queue = sqs.create_queue(QueueName=str(uuid4())[0:6])
    with pytest.raises(ClientError) as e:
        queue.send_message(
            MessageBody="derp",
            MessageAttributes={
                "öther_encodings": {"DataType": "String", "StringValue": "str"},
            },
        )
    ex = e.value
    assert ex.response["Error"]["Code"] == "MessageAttributesInvalid"
    assert ex.response["Error"]["Message"] == (
        "The message attribute name 'öther_encodings' is invalid. "
        "Attribute name can contain A-Z, a-z, 0-9, underscore (_), "
        "hyphen (-), and period (.) characters."
    )


@mock_aws
def test_message_with_string_attributes():
    sqs = boto3.resource("sqs", region_name=REGION)
    queue = sqs.create_queue(QueueName=str(uuid4())[0:6])
    msg = queue.send_message(
        MessageBody="derp",
        MessageAttributes={
            "id": {
                "StringValue": "2018fc74-4f77-1a5a-1be0-c2d037d5052b",
                "DataType": "String",
            },
            "contentType": {"StringValue": "application/json", "DataType": "String"},
            "timestamp": {
                "StringValue": "1602845432024",
                "DataType": "Number.java.lang.Long",
            },
        },
    )
    assert msg.get("MD5OfMessageBody") == "58fd9edd83341c29f1aebba81c31e257"
    assert msg.get("MD5OfMessageAttributes") == "b12289320bb6e494b18b645ef562b4a9"
    assert " \n" not in msg.get("MessageId")

    messages = queue.receive_messages()
    assert len(messages) == 1


@mock_aws
def test_message_with_binary_attribute():
    sqs = boto3.resource("sqs", region_name=REGION)
    queue = sqs.create_queue(QueueName=str(uuid4())[0:6])
    msg = queue.send_message(
        MessageBody="derp",
        MessageAttributes={
            "id": {
                "StringValue": "453ae55e-f03b-21a6-a4b1-70c2e2e8fe71",
                "DataType": "String",
            },
            "mybin": {"BinaryValue": "kekchebukek", "DataType": "Binary"},
            "timestamp": {
                "StringValue": "1603134247654",
                "DataType": "Number.java.lang.Long",
            },
            "contentType": {"StringValue": "application/json", "DataType": "String"},
        },
    )
    assert msg.get("MD5OfMessageBody") == "58fd9edd83341c29f1aebba81c31e257"
    assert msg.get("MD5OfMessageAttributes") == "049075255ebc53fb95f7f9f3cedf3c50"
    assert " \n" not in msg.get("MessageId")

    messages = queue.receive_messages()
    assert len(messages) == 1


@mock_aws
def test_message_with_attributes_have_labels():
    sqs = boto3.resource("sqs", region_name=REGION)
    queue = sqs.create_queue(QueueName=str(uuid4())[0:6])
    msg = queue.send_message(
        MessageBody="derp",
        MessageAttributes={
            "timestamp": {
                "DataType": "Number.java.lang.Long",
                "StringValue": "1493147359900",
            }
        },
    )
    assert msg.get("MD5OfMessageBody") == "58fd9edd83341c29f1aebba81c31e257"
    assert msg.get("MD5OfMessageAttributes") == "2e2e4876d8e0bd6b8c2c8f556831c349"
    assert " \n" not in msg.get("MessageId")

    messages = queue.receive_messages()
    assert len(messages) == 1


@mock_aws
def test_message_with_attributes_invalid_datatype():
    sqs = boto3.resource("sqs", region_name=REGION)
    queue = sqs.create_queue(QueueName=str(uuid4())[0:6])

    with pytest.raises(ClientError) as e:
        queue.send_message(
            MessageBody="derp",
            MessageAttributes={
                "timestamp": {
                    "DataType": "InvalidNumber",
                    "StringValue": "149314735990a",
                }
            },
        )
    ex = e.value
    assert ex.response["Error"]["Code"] == "MessageAttributesInvalid"
    assert ex.response["Error"]["Message"] == (
        "The message attribute 'timestamp' has an invalid message "
        "attribute type, the set of supported type "
        "prefixes is Binary, Number, and String."
    )


@mock_aws
def test_send_message_with_message_group_id():
    sqs = boto3.resource("sqs", region_name=REGION)
    queue = sqs.create_queue(
        QueueName=f"{str(uuid4())[0:6]}.fifo", Attributes={"FifoQueue": "true"}
    )

    queue.send_message(
        MessageBody="mydata",
        MessageDeduplicationId="dedupe_id_1",
        MessageGroupId="group_id_1",
    )

    messages = queue.receive_messages(
        AttributeNames=["MessageDeduplicationId", "MessageGroupId"]
    )
    assert len(messages) == 1

    message_attributes = messages[0].attributes
    assert "MessageGroupId" in message_attributes
    assert message_attributes["MessageGroupId"] == "group_id_1"
    assert "MessageDeduplicationId" in message_attributes
    assert message_attributes["MessageDeduplicationId"] == "dedupe_id_1"


@mock_aws
def test_send_message_with_message_group_id_standard_queue():
    sqs = boto3.resource("sqs", region_name=REGION)
    queue = sqs.create_queue(QueueName=str(uuid4())[0:6])

    with pytest.raises(ClientError) as ex:
        queue.send_message(MessageBody="mydata", MessageGroupId="group_id_1")

    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert err["Message"] == (
        "Value group_id_1 for parameter MessageGroupId is invalid. "
        "Reason: The request include parameter that is not valid for this queue type."
    )


@mock_aws
def test_send_message_with_unicode_characters():
    body_one = "Héllo!😀"

    sqs = boto3.resource("sqs", region_name=REGION)
    queue = sqs.create_queue(QueueName=str(uuid4())[0:6])
    queue.send_message(MessageBody=body_one)

    messages = queue.receive_messages()
    message_body = messages[0].body

    assert message_body == body_one


@mock_aws
def test_set_queue_attributes():
    sqs = boto3.resource("sqs", region_name=REGION)
    queue = sqs.create_queue(QueueName=str(uuid4())[0:6])

    assert queue.attributes["VisibilityTimeout"] == "30"

    queue.set_attributes(Attributes={"VisibilityTimeout": "45"})
    assert queue.attributes["VisibilityTimeout"] == "45"


def _get_common_url(region):
    # Different versions of botocore return different URLs
    # See https://github.com/boto/botocore/issues/2705
    boto3_version = sys.modules["botocore"].__version__
    if LooseVersion(boto3_version) >= LooseVersion("1.29.0"):
        return f"https://sqs.{region}.amazonaws.com"
    common_name_enabled = (
        os.environ.get("BOTO_DISABLE_COMMONNAME", "false").lower() == "false"
    )
    return (
        f"https://{region}.queue.amazonaws.com"
        if common_name_enabled
        else f"https://sqs.{region}.amazonaws.com"
    )


@mock_aws
def test_create_queues_in_multiple_region():
    w1 = boto3.client("sqs", region_name="us-west-1")
    w1_name = str(uuid4())[0:6]
    w1.create_queue(QueueName=w1_name)

    w2 = boto3.client("sqs", region_name="us-west-2")
    w2_name = str(uuid4())[0:6]
    w2.create_queue(QueueName=w2_name)

    boto_common_url = _get_common_url("us-west-1")
    base_url = "http://localhost:5000" if settings.TEST_SERVER_MODE else boto_common_url
    assert f"{base_url}/{ACCOUNT_ID}/{w1_name}" in w1.list_queues()["QueueUrls"]
    assert f"{base_url}/{ACCOUNT_ID}/{w2_name}" not in w1.list_queues()["QueueUrls"]

    boto_common_url = _get_common_url("us-west-2")
    base_url = "http://localhost:5000" if settings.TEST_SERVER_MODE else boto_common_url
    assert f"{base_url}/{ACCOUNT_ID}/{w1_name}" not in w2.list_queues()["QueueUrls"]
    assert f"{base_url}/{ACCOUNT_ID}/{w2_name}" in w2.list_queues()["QueueUrls"]


@mock_aws
def test_get_queue_with_prefix():
    conn = boto3.client("sqs", region_name="us-west-1")
    conn.create_queue(QueueName=str(uuid4())[0:6])
    q_name1 = str(uuid4())[0:6]
    conn.create_queue(QueueName=q_name1)
    prefix = str(uuid4())[0:6]
    q_name2 = f"{prefix}-test"
    conn.create_queue(QueueName=q_name2)

    boto_common_url = _get_common_url("us-west-1")
    base_url = "http://localhost:5000" if settings.TEST_SERVER_MODE else boto_common_url
    expected_url1 = f"{base_url}/{ACCOUNT_ID}/{q_name1}"
    expected_url2 = f"{base_url}/{ACCOUNT_ID}/{q_name2}"

    all_urls = conn.list_queues()["QueueUrls"]
    assert expected_url1 in all_urls
    assert expected_url2 in all_urls

    queue = conn.list_queues(QueueNamePrefix=prefix)["QueueUrls"]
    assert len(queue) == 1

    assert queue[0] == expected_url2


@mock_aws
def test_delete_queue():
    sqs = boto3.resource("sqs", region_name=REGION)
    conn = boto3.client("sqs", region_name=REGION)
    q_name = str(uuid4())[0:6]
    q_resp = conn.create_queue(QueueName=q_name, Attributes={"VisibilityTimeout": "3"})
    queue = sqs.Queue(q_resp["QueueUrl"])

    all_urls = conn.list_queues()["QueueUrls"]
    assert q_name in [u[u.rfind("/") + 1 :] for u in all_urls]

    queue.delete()

    all_urls = conn.list_queues().get("QueueUrls", [])
    assert q_name not in [u[u.rfind("/") + 1 :] for u in all_urls]


@mock_aws
def test_delete_queue_error_not_exists():
    client = boto3.client("sqs", region_name=REGION)

    with pytest.raises(ClientError) as e:
        client.delete_queue(
            QueueUrl=f"https://queue.amazonaws.com/{ACCOUNT_ID}/not-exists"
        )

    ex = e.value
    assert ex.operation_name == "DeleteQueue"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "AWS.SimpleQueueService.NonExistentQueue" in ex.response["Error"]["Code"]
    assert ex.response["Error"]["Message"] == (
        "The specified queue does not exist for this wsdl version."
    )


@mock_aws
def test_get_queue_attributes():
    client = boto3.client("sqs", region_name=REGION)

    dlq_resp = client.create_queue(QueueName="test-dlr-queue")
    dlq_arn1 = client.get_queue_attributes(
        QueueUrl=dlq_resp["QueueUrl"], AttributeNames=["QueueArn"]
    )["Attributes"]["QueueArn"]

    q_name = str(uuid4())[0:6]
    response = client.create_queue(
        QueueName=q_name,
        Attributes={
            "RedrivePolicy": json.dumps(
                {"deadLetterTargetArn": dlq_arn1, "maxReceiveCount": 2}
            ),
        },
    )
    queue_url = response["QueueUrl"]

    response = client.get_queue_attributes(QueueUrl=queue_url, AttributeNames=["All"])

    assert response["Attributes"]["ApproximateNumberOfMessages"] == "0"
    assert response["Attributes"]["ApproximateNumberOfMessagesDelayed"] == "0"
    assert response["Attributes"]["ApproximateNumberOfMessagesNotVisible"] == "0"
    assert isinstance(response["Attributes"]["CreatedTimestamp"], str)
    assert response["Attributes"]["DelaySeconds"] == "0"
    assert isinstance(response["Attributes"]["LastModifiedTimestamp"], str)
    assert response["Attributes"]["MaximumMessageSize"] == "262144"
    assert response["Attributes"]["MessageRetentionPeriod"] == "345600"
    assert response["Attributes"]["QueueArn"] == (
        f"arn:aws:sqs:{REGION}:{ACCOUNT_ID}:{q_name}"
    )
    assert response["Attributes"]["ReceiveMessageWaitTimeSeconds"] == "0"
    assert response["Attributes"]["VisibilityTimeout"] == "30"

    response = client.get_queue_attributes(
        QueueUrl=queue_url,
        AttributeNames=[
            "ApproximateNumberOfMessages",
            "MaximumMessageSize",
            "QueueArn",
            "RedrivePolicy",
            "VisibilityTimeout",
        ],
    )

    assert response["Attributes"] == {
        "ApproximateNumberOfMessages": "0",
        "MaximumMessageSize": "262144",
        "QueueArn": f"arn:aws:sqs:{REGION}:{ACCOUNT_ID}:{q_name}",
        "VisibilityTimeout": "30",
        "RedrivePolicy": json.dumps(
            {"deadLetterTargetArn": dlq_arn1, "maxReceiveCount": 2}
        ),
    }

    # should not return any attributes, if it was not set before
    response = client.get_queue_attributes(
        QueueUrl=queue_url, AttributeNames=["KmsMasterKeyId"]
    )

    assert "Attributes" not in response


@mock_aws
def test_get_queue_attributes_errors():
    client = boto3.client("sqs", region_name=REGION)
    response = client.create_queue(QueueName=str(uuid4())[0:6])
    queue_url = response["QueueUrl"]

    with pytest.raises(ClientError) as client_error:
        client.get_queue_attributes(
            QueueUrl=queue_url,
            AttributeNames=["QueueArn", "not-existing", "VisibilityTimeout"],
        )
    assert (
        client_error.value.response["Error"]["Message"]
        == "Unknown Attribute not-existing."
    )

    with pytest.raises(ClientError) as client_error:
        client.get_queue_attributes(QueueUrl=queue_url, AttributeNames=[""])
    assert client_error.value.response["Error"]["Message"] == "Unknown Attribute ."

    with pytest.raises(ClientError) as client_error:
        client.get_queue_attributes(QueueUrl=queue_url, AttributeNames=[])
    assert client_error.value.response["Error"]["Message"] == "Unknown Attribute ."


@mock_aws
def test_get_queue_attributes_error_not_exists():
    # given
    client = boto3.client("sqs", region_name=REGION)

    # when
    with pytest.raises(ClientError) as e:
        client.get_queue_attributes(
            QueueUrl=f"https://queue.amazonaws.com/{ACCOUNT_ID}/not-exists"
        )

    # then
    ex = e.value
    assert ex.operation_name == "GetQueueAttributes"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "AWS.SimpleQueueService.NonExistentQueue" in ex.response["Error"]["Code"]
    assert ex.response["Error"]["Message"] == (
        "The specified queue does not exist for this wsdl version."
    )


@mock_aws
def test_set_queue_attribute():
    sqs = boto3.resource("sqs", region_name=REGION)
    conn = boto3.client("sqs", region_name=REGION)
    q_resp = conn.create_queue(
        QueueName=str(uuid4())[0:6], Attributes={"VisibilityTimeout": "3"}
    )

    queue = sqs.Queue(q_resp["QueueUrl"])
    assert queue.attributes["VisibilityTimeout"] == "3"

    queue.set_attributes(Attributes={"VisibilityTimeout": "45"})
    queue = sqs.Queue(q_resp["QueueUrl"])
    assert queue.attributes["VisibilityTimeout"] == "45"


@mock_aws
def test_send_receive_message_without_attributes():
    sqs = boto3.resource("sqs", region_name=REGION)
    conn = boto3.client("sqs", region_name=REGION)
    q_resp = conn.create_queue(QueueName=str(uuid4())[0:6])
    queue = sqs.Queue(q_resp["QueueUrl"])

    body_one = "this is a test message"
    body_two = "this is another test message"

    queue.send_message(MessageBody=body_one)
    queue.send_message(MessageBody=body_two)

    messages = conn.receive_message(QueueUrl=queue.url, MaxNumberOfMessages=2)[
        "Messages"
    ]

    message1 = messages[0]
    message2 = messages[1]

    assert message1["Body"] == body_one
    assert message2["Body"] == body_two

    assert "MD5OfMessageAttributes" not in message1
    assert "MD5OfMessageAttributes" not in message2

    assert "Attributes" not in message1
    assert "Attributes" not in message2


@mock_aws
def test_send_receive_message_with_attributes():
    sqs = boto3.resource("sqs", region_name=REGION)
    conn = boto3.client("sqs", region_name=REGION)
    q_resp = conn.create_queue(QueueName=str(uuid4())[0:6])
    queue = sqs.Queue(q_resp["QueueUrl"])

    body_one = "this is a test message"
    body_two = "this is another test message"

    queue.send_message(
        MessageBody=body_one,
        MessageAttributes={
            "timestamp": {"StringValue": "1493147359900", "DataType": "Number"}
        },
    )

    queue.send_message(
        MessageBody=body_two,
        MessageAttributes={
            "timestamp": {"StringValue": "1493147359901", "DataType": "Number"}
        },
    )

    messages = conn.receive_message(
        QueueUrl=queue.url, MaxNumberOfMessages=2, MessageAttributeNames=["timestamp"]
    )["Messages"]

    message1 = messages[0]
    message2 = messages[1]

    assert message1.get("Body") == body_one
    assert message2.get("Body") == body_two

    assert message1.get("MD5OfMessageAttributes") == "235c5c510d26fb653d073faed50ae77c"
    assert message2.get("MD5OfMessageAttributes") == "994258b45346a2cc3f9cbb611aa7af30"


@mock_aws
def test_send_receive_message_with_attributes_with_labels():
    sqs = boto3.resource("sqs", region_name=REGION)
    conn = boto3.client("sqs", region_name=REGION)
    q_resp = conn.create_queue(QueueName=str(uuid4())[0:6])
    queue = sqs.Queue(q_resp["QueueUrl"])

    body_one = "this is a test message"
    body_two = "this is another test message"

    queue.send_message(
        MessageBody=body_one,
        MessageAttributes={
            "timestamp": {
                "StringValue": "1493147359900",
                "DataType": "Number.java.lang.Long",
            }
        },
    )

    queue.send_message(
        MessageBody=body_two,
        MessageAttributes={
            "timestamp": {
                "StringValue": "1493147359901",
                "DataType": "Number.java.lang.Long",
            }
        },
    )

    messages = conn.receive_message(
        QueueUrl=queue.url, MaxNumberOfMessages=2, MessageAttributeNames=["timestamp"]
    )["Messages"]

    message1 = messages[0]
    message2 = messages[1]

    assert message1.get("Body") == body_one
    assert message2.get("Body") == body_two

    assert message1.get("MD5OfMessageAttributes") == "2e2e4876d8e0bd6b8c2c8f556831c349"
    assert message2.get("MD5OfMessageAttributes") == "cfa7c73063c6e2dbf9be34232a1978cf"

    response = queue.send_message(
        MessageBody="test message",
        MessageAttributes={
            "somevalue": {"StringValue": "somevalue", "DataType": "String.custom"}
        },
    )

    assert response.get("MD5OfMessageAttributes") == "9e05cca738e70ff6c6041e82d5e77ef1"


@mock_aws
def test_receive_message_with_xml_content():
    sqs = boto3.client("sqs", region_name="eu-west-2")
    queue_url = sqs.create_queue(QueueName=str(uuid4())[0:6])["QueueUrl"]
    original_payload = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<feed xmlns="http://www.w3.org/2005/Atom"/>'
    )
    data = {"Payload": {"DataType": "String", "StringValue": original_payload}}

    sqs.send_message(
        QueueUrl=queue_url, MessageBody="NSWSS Atom Feed", MessageAttributes=data
    )

    messages = sqs.receive_message(
        QueueUrl=queue_url,
        MessageAttributeNames=("Payload",),
        MaxNumberOfMessages=1,
        VisibilityTimeout=0,
    )["Messages"]

    attr = messages[0]["MessageAttributes"]["Payload"]["StringValue"]
    assert attr == original_payload


@mock_aws
def test_change_message_visibility_than_permitted():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Cant manipulate time in server mode")

    sqs = boto3.resource("sqs", region_name=REGION)
    conn = boto3.client("sqs", region_name=REGION)

    with freeze_time("2015-01-01 12:00:00"):
        q_resp = conn.create_queue(QueueName="test-queue-visibility")
        queue = sqs.Queue(q_resp["QueueUrl"])
        queue.send_message(MessageBody="derp")
        messages = conn.receive_message(QueueUrl=queue.url)
        assert len(messages.get("Messages")) == 1

        conn.change_message_visibility(
            QueueUrl=queue.url,
            ReceiptHandle=messages.get("Messages")[0].get("ReceiptHandle"),
            VisibilityTimeout=360,
        )

    with freeze_time("2015-01-01 12:05:00"):
        with pytest.raises(ClientError) as err:
            conn.change_message_visibility(
                QueueUrl=queue.url,
                ReceiptHandle=messages.get("Messages")[0].get("ReceiptHandle"),
                VisibilityTimeout=43200,
            )

        ex = err.value
        assert ex.operation_name == "ChangeMessageVisibility"
        assert ex.response["Error"]["Code"] == "InvalidParameterValue"


@mock_aws
def test_send_receive_message_timestamps():
    sqs = boto3.resource("sqs", region_name=REGION)
    conn = boto3.client("sqs", region_name=REGION)
    q_resp = conn.create_queue(QueueName=str(uuid4())[0:6])
    queue = sqs.Queue(q_resp["QueueUrl"])

    response = queue.send_message(MessageBody="derp")
    assert response["ResponseMetadata"]["RequestId"]

    messages = conn.receive_message(
        QueueUrl=queue.url,
        AttributeNames=["ApproximateFirstReceiveTimestamp", "SentTimestamp"],
        MaxNumberOfMessages=1,
    )["Messages"]

    message = messages[0]
    sent_timestamp = message.get("Attributes").get("SentTimestamp")
    approximate_first_receive_timestamp = message.get("Attributes").get(
        "ApproximateFirstReceiveTimestamp"
    )

    try:
        int(sent_timestamp)
    except ValueError:
        assert False, "sent_timestamp not an int"
    try:
        int(approximate_first_receive_timestamp)
    except ValueError:
        assert False, "aproximate_first_receive_timestamp not an int"


@mock_aws
@pytest.mark.parametrize(
    "attribute_name,expected",
    [
        (
            "All",
            {
                "ApproximateFirstReceiveTimestamp": lambda x: x,
                "ApproximateReceiveCount": lambda x: x == "1",
                "MessageDeduplicationId": lambda x: x is None,
                "MessageGroupId": lambda x: x is None,
                "SenderId": lambda x: x,
                "SentTimestamp": lambda x: x,
                "SequenceNumber": lambda x: x is None,
            },
        ),
        (
            "ApproximateFirstReceiveTimestamp",
            {
                "ApproximateFirstReceiveTimestamp": lambda x: x,
                "ApproximateReceiveCount": lambda x: x is None,
                "MessageDeduplicationId": lambda x: x is None,
                "MessageGroupId": lambda x: x is None,
                "SenderId": lambda x: x is None,
                "SentTimestamp": lambda x: x is None,
                "SequenceNumber": lambda x: x is None,
            },
        ),
        (
            "ApproximateReceiveCount",
            {
                "ApproximateFirstReceiveTimestamp": lambda x: x is None,
                "ApproximateReceiveCount": lambda x: x == "1",
                "MessageDeduplicationId": lambda x: x is None,
                "MessageGroupId": lambda x: x is None,
                "SenderId": lambda x: x is None,
                "SentTimestamp": lambda x: x is None,
                "SequenceNumber": lambda x: x is None,
            },
        ),
        (
            "SenderId",
            {
                "ApproximateFirstReceiveTimestamp": lambda x: x is None,
                "ApproximateReceiveCount": lambda x: x is None,
                "MessageDeduplicationId": lambda x: x is None,
                "MessageGroupId": lambda x: x is None,
                "SenderId": lambda x: x,
                "SentTimestamp": lambda x: x is None,
                "SequenceNumber": lambda x: x is None,
            },
        ),
        (
            "SentTimestamp",
            {
                "ApproximateFirstReceiveTimestamp": lambda x: x is None,
                "ApproximateReceiveCount": lambda x: x is None,
                "MessageDeduplicationId": lambda x: x is None,
                "MessageGroupId": lambda x: x is None,
                "SenderId": lambda x: x is None,
                "SentTimestamp": lambda x: x,
                "SequenceNumber": lambda x: x is None,
            },
        ),
    ],
    ids=[
        "All",
        "ApproximateFirstReceiveTimestamp",
        "ApproximateReceiveCount",
        "SenderId",
        "SentTimestamp",
    ],
)
def test_send_receive_message_with_attribute_name(attribute_name, expected):
    sqs = boto3.resource("sqs", region_name=REGION)
    client = boto3.client("sqs", region_name=REGION)
    q_resp = client.create_queue(QueueName=str(uuid4())[0:6])
    queue = sqs.Queue(q_resp["QueueUrl"])

    body_one = "this is a test message"
    body_two = "this is another test message"

    queue.send_message(MessageBody=body_one)
    queue.send_message(MessageBody=body_two)

    messages = client.receive_message(
        QueueUrl=queue.url, AttributeNames=[attribute_name], MaxNumberOfMessages=2
    )["Messages"]

    message1 = messages[0]
    message2 = messages[1]

    assert message1["Body"] == body_one
    assert message2["Body"] == body_two

    assert "MD5OfMessageAttributes" not in message1
    assert "MD5OfMessageAttributes" not in message2

    assert expected["ApproximateFirstReceiveTimestamp"](
        message1["Attributes"].get("ApproximateFirstReceiveTimestamp")
    )
    assert expected["ApproximateReceiveCount"](
        message1["Attributes"].get("ApproximateReceiveCount")
    )
    assert expected["MessageDeduplicationId"](
        message1["Attributes"].get("MessageDeduplicationId")
    )
    assert expected["MessageGroupId"](message1["Attributes"].get("MessageGroupId"))
    assert expected["SenderId"](message1["Attributes"].get("SenderId"))
    assert expected["SentTimestamp"](message1["Attributes"].get("SentTimestamp"))
    assert expected["SequenceNumber"](message1["Attributes"].get("SequenceNumber"))

    assert expected["ApproximateFirstReceiveTimestamp"](
        message2["Attributes"].get("ApproximateFirstReceiveTimestamp")
    )
    assert expected["ApproximateReceiveCount"](
        message2["Attributes"].get("ApproximateReceiveCount")
    )
    assert expected["MessageDeduplicationId"](
        message2["Attributes"].get("MessageDeduplicationId")
    )
    assert expected["MessageGroupId"](message2["Attributes"].get("MessageGroupId"))
    assert expected["SenderId"](message2["Attributes"].get("SenderId"))
    assert expected["SentTimestamp"](message2["Attributes"].get("SentTimestamp"))
    assert expected["SequenceNumber"](message2["Attributes"].get("SequenceNumber"))


@mock_aws
@pytest.mark.parametrize(
    "attribute_name,expected",
    [
        (
            "All",
            {
                "ApproximateFirstReceiveTimestamp": lambda x: x,
                "ApproximateReceiveCount": lambda x: x == "1",
                "MessageDeduplicationId": lambda x: x == "123",
                "MessageGroupId": lambda x: x == "456",
                "SenderId": lambda x: x,
                "SentTimestamp": lambda x: x,
                "SequenceNumber": lambda x: x,
            },
        ),
        (
            "ApproximateFirstReceiveTimestamp",
            {
                "ApproximateFirstReceiveTimestamp": lambda x: x,
                "ApproximateReceiveCount": lambda x: x is None,
                "MessageDeduplicationId": lambda x: x is None,
                "MessageGroupId": lambda x: x is None,
                "SenderId": lambda x: x is None,
                "SentTimestamp": lambda x: x is None,
                "SequenceNumber": lambda x: x is None,
            },
        ),
        (
            "ApproximateReceiveCount",
            {
                "ApproximateFirstReceiveTimestamp": lambda x: x is None,
                "ApproximateReceiveCount": lambda x: x == "1",
                "MessageDeduplicationId": lambda x: x is None,
                "MessageGroupId": lambda x: x is None,
                "SenderId": lambda x: x is None,
                "SentTimestamp": lambda x: x is None,
                "SequenceNumber": lambda x: x is None,
            },
        ),
        (
            "MessageDeduplicationId",
            {
                "ApproximateFirstReceiveTimestamp": lambda x: x is None,
                "ApproximateReceiveCount": lambda x: x is None,
                "MessageDeduplicationId": lambda x: x == "123",
                "MessageGroupId": lambda x: x is None,
                "SenderId": lambda x: x is None,
                "SentTimestamp": lambda x: x is None,
                "SequenceNumber": lambda x: x is None,
            },
        ),
        (
            "MessageGroupId",
            {
                "ApproximateFirstReceiveTimestamp": lambda x: x is None,
                "ApproximateReceiveCount": lambda x: x is None,
                "MessageDeduplicationId": lambda x: x is None,
                "MessageGroupId": lambda x: x == "456",
                "SenderId": lambda x: x is None,
                "SentTimestamp": lambda x: x is None,
                "SequenceNumber": lambda x: x is None,
            },
        ),
        (
            "SenderId",
            {
                "ApproximateFirstReceiveTimestamp": lambda x: x is None,
                "ApproximateReceiveCount": lambda x: x is None,
                "MessageDeduplicationId": lambda x: x is None,
                "MessageGroupId": lambda x: x is None,
                "SenderId": lambda x: x,
                "SentTimestamp": lambda x: x is None,
                "SequenceNumber": lambda x: x is None,
            },
        ),
        (
            "SentTimestamp",
            {
                "ApproximateFirstReceiveTimestamp": lambda x: x is None,
                "ApproximateReceiveCount": lambda x: x is None,
                "MessageDeduplicationId": lambda x: x is None,
                "MessageGroupId": lambda x: x is None,
                "SenderId": lambda x: x is None,
                "SentTimestamp": lambda x: x,
                "SequenceNumber": lambda x: x is None,
            },
        ),
        (
            "SequenceNumber",
            {
                "ApproximateFirstReceiveTimestamp": lambda x: x is None,
                "ApproximateReceiveCount": lambda x: x is None,
                "MessageDeduplicationId": lambda x: x is None,
                "MessageGroupId": lambda x: x is None,
                "SenderId": lambda x: x is None,
                "SentTimestamp": lambda x: x is None,
                "SequenceNumber": lambda x: x,
            },
        ),
    ],
    ids=[
        "All",
        "ApproximateFirstReceiveTimestamp",
        "ApproximateReceiveCount",
        "MessageDeduplicationId",
        "MessageGroupId",
        "SenderId",
        "SentTimestamp",
        "SequenceNumber",
    ],
)
def test_fifo_send_receive_message_with_attribute_name(attribute_name, expected):
    client = boto3.client("sqs", region_name=REGION)
    queue_url = client.create_queue(
        QueueName=f"{str(uuid4())[0:6]}.fifo", Attributes={"FifoQueue": "true"}
    )["QueueUrl"]

    body = "this is a test message"

    client.send_message(
        QueueUrl=queue_url,
        MessageBody=body,
        MessageDeduplicationId="123",
        MessageGroupId="456",
    )

    message = client.receive_message(
        QueueUrl=queue_url, AttributeNames=[attribute_name], MaxNumberOfMessages=2
    )["Messages"][0]

    assert message["Body"] == body

    assert "MD5OfMessageAttributes" not in message

    assert expected["ApproximateFirstReceiveTimestamp"](
        message["Attributes"].get("ApproximateFirstReceiveTimestamp")
    )
    assert expected["ApproximateReceiveCount"](
        message["Attributes"].get("ApproximateReceiveCount")
    )
    assert expected["MessageDeduplicationId"](
        message["Attributes"].get("MessageDeduplicationId")
    )
    assert expected["MessageGroupId"](message["Attributes"].get("MessageGroupId"))
    assert expected["SenderId"](message["Attributes"].get("SenderId"))
    assert expected["SentTimestamp"](message["Attributes"].get("SentTimestamp"))
    assert expected["SequenceNumber"](message["Attributes"].get("SequenceNumber"))


@mock_aws
def test_get_queue_attributes_no_param():
    """Test Attributes-key is not returned when no AttributeNames-parameter."""
    sqs = boto3.client("sqs", region_name="ap-northeast-3")
    queue_url = sqs.create_queue(QueueName=str(uuid4())[0:6])["QueueUrl"]

    queue_attrs = sqs.get_queue_attributes(QueueUrl=queue_url)
    assert "Attributes" not in queue_attrs

    queue_attrs = sqs.get_queue_attributes(QueueUrl=queue_url, AttributeNames=["All"])
    assert "Attributes" in queue_attrs


@mock_aws
def test_max_number_of_messages_invalid_param():
    sqs = boto3.resource("sqs", region_name=REGION)
    queue = sqs.create_queue(QueueName=str(uuid4())[0:6])

    with pytest.raises(ClientError):
        queue.receive_messages(MaxNumberOfMessages=11)

    with pytest.raises(ClientError):
        queue.receive_messages(MaxNumberOfMessages=0)

    # no error but also no messages returned
    queue.receive_messages(MaxNumberOfMessages=1, WaitTimeSeconds=0)


@mock_aws
def test_wait_time_seconds_invalid_param():
    sqs = boto3.resource("sqs", region_name=REGION)
    queue = sqs.create_queue(QueueName=str(uuid4())[0:6])

    with pytest.raises(ClientError):
        queue.receive_messages(WaitTimeSeconds=-1)

    with pytest.raises(ClientError):
        queue.receive_messages(WaitTimeSeconds=21)

    # no error but also no messages returned
    queue.receive_messages(WaitTimeSeconds=0)


@mock_aws
def test_receive_messages_with_wait_seconds_timeout_of_zero():
    """
    test that zero messages is returned with a wait_seconds_timeout of zero,
    previously this created an infinite loop and nothing was returned
    :return:
    """

    sqs = boto3.resource("sqs", region_name=REGION)
    queue = sqs.create_queue(QueueName=str(uuid4())[0:6])

    messages = queue.receive_messages(WaitTimeSeconds=0)
    assert messages == []


@mock_aws
def test_send_message_with_xml_characters():
    sqs = boto3.resource("sqs", region_name=REGION)
    client = boto3.client("sqs", region_name=REGION)
    queue = sqs.create_queue(QueueName=str(uuid4())[0:6])

    body_one = "< & >"

    queue.send_message(MessageBody=body_one)

    messages = client.receive_message(QueueUrl=queue.url)["Messages"]

    assert messages[0]["Body"] == body_one


@mock_aws
def test_send_message_with_delay():
    sqs = boto3.resource("sqs", region_name=REGION)
    queue = sqs.create_queue(QueueName=str(uuid4())[0:6])

    body_one = "this is a test message"
    body_two = "this is another test message"

    queue.send_message(MessageBody=body_one, DelaySeconds=3)
    queue.send_message(MessageBody=body_two)

    messages = queue.receive_messages()
    assert len(messages) == 1

    assert messages[0].body == body_two

    messages = queue.receive_messages()
    assert len(messages) == 0


@mock_aws
def test_send_message_with_message_delay_overriding_queue_delay():
    sqs = boto3.client("sqs", region_name=REGION)
    name = str(uuid4())[0:6]
    # By default, all messages on this queue are delayed
    resp = sqs.create_queue(QueueName=name, Attributes={"DelaySeconds": "10"})
    queue_url = resp["QueueUrl"]
    # But this particular message should have no delay
    sqs.send_message(QueueUrl=queue_url, MessageBody="test", DelaySeconds=0)
    resp = sqs.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=10)
    assert len(resp["Messages"]) == 1


@mock_aws
def test_send_large_message_fails():
    sqs = boto3.resource("sqs", region_name=REGION)
    queue = sqs.create_queue(QueueName=str(uuid4())[0:6])

    body = "test message" * 200000
    with pytest.raises(ClientError) as ex:
        queue.send_message(MessageBody=body)
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert err["Message"] == (
        "One or more parameters are invalid. Reason: Message must be shorter than 262144 bytes."
    )


@mock_aws
def test_message_becomes_inflight_when_received():
    sqs = boto3.resource("sqs", region_name="eu-west-1")
    queue = sqs.create_queue(
        QueueName=str(uuid4())[0:6], Attributes={"VisibilityTimeout ": "2"}
    )

    assert queue.attributes["ApproximateNumberOfMessages"] == "0"

    body = "this is a test message"
    queue.send_message(MessageBody=body)

    queue.reload()
    assert queue.attributes["ApproximateNumberOfMessages"] == "1"

    messages = queue.receive_messages()
    assert len(messages) == 1

    queue.reload()
    assert queue.attributes["ApproximateNumberOfMessages"] == "0"

    # Wait
    time.sleep(3)

    queue.reload()
    assert queue.attributes["ApproximateNumberOfMessages"] == "1"


@mock_aws
def test_receive_message_with_explicit_visibility_timeout():
    sqs = boto3.resource("sqs", region_name=REGION)
    queue = sqs.create_queue(
        QueueName=str(uuid4())[0:6], Attributes={"VisibilityTimeout ": "1"}
    )

    assert queue.attributes["ApproximateNumberOfMessages"] == "0"

    body = "this is a test message"
    queue.send_message(MessageBody=body)

    queue.reload()
    assert queue.attributes["ApproximateNumberOfMessages"] == "1"

    messages = queue.receive_messages(VisibilityTimeout=0)
    assert len(messages) == 1

    queue.reload()
    assert queue.attributes["ApproximateNumberOfMessages"] == "1"


@mock_aws
def test_change_message_visibility():
    sqs = boto3.resource("sqs", region_name=REGION)
    queue = sqs.create_queue(
        QueueName=str(uuid4())[0:6], Attributes={"VisibilityTimeout ": "2"}
    )

    body = "this is a test message"
    queue.send_message(MessageBody=body)

    queue.reload()
    assert queue.attributes["ApproximateNumberOfMessages"] == "1"
    messages = queue.receive_messages()

    assert len(messages) == 1

    queue.reload()
    assert queue.attributes["ApproximateNumberOfMessages"] == "0"

    messages[0].change_visibility(VisibilityTimeout=2)

    # Wait
    time.sleep(1)

    # Message is not visible
    queue.reload()
    assert queue.attributes["ApproximateNumberOfMessages"] == "0"

    time.sleep(2)

    # Message now becomes visible
    queue.reload()
    assert queue.attributes["ApproximateNumberOfMessages"] == "1"

    messages = queue.receive_messages()
    messages[0].delete()
    queue.reload()
    assert queue.attributes["ApproximateNumberOfMessages"] == "0"


@mock_aws
def test_change_message_visibility_on_unknown_receipt_handle():
    sqs = boto3.resource("sqs", region_name=REGION)
    conn = boto3.client("sqs", region_name=REGION)
    queue = sqs.create_queue(
        QueueName=str(uuid4())[0:6], Attributes={"VisibilityTimeout": "2"}
    )

    with pytest.raises(ClientError) as exc:
        conn.change_message_visibility(
            QueueUrl=queue.url, ReceiptHandle="unknown-stuff", VisibilityTimeout=432
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ReceiptHandleIsInvalid"
    assert err["Message"] == "The input receipt handle is invalid."


@mock_aws
def test_queue_length():
    sqs = boto3.resource("sqs", region_name=REGION)
    queue = sqs.create_queue(
        QueueName=str(uuid4())[0:6], Attributes={"VisibilityTimeout ": "2"}
    )

    queue.send_message(MessageBody="this is a test message")
    queue.send_message(MessageBody="this is another test message")

    queue.reload()
    assert queue.attributes["ApproximateNumberOfMessages"] == "2"


@mock_aws
def test_delete_batch_operation():
    sqs = boto3.resource("sqs", region_name=REGION)
    queue = sqs.create_queue(
        QueueName=str(uuid4())[0:6], Attributes={"VisibilityTimeout ": "2"}
    )

    queue.send_message(MessageBody="test message 1")
    queue.send_message(MessageBody="test message 2")
    queue.send_message(MessageBody="test message 3")

    messages = queue.receive_messages(MaxNumberOfMessages=2)
    queue.delete_messages(
        Entries=[
            {"Id": m.message_id, "ReceiptHandle": m.receipt_handle} for m in messages
        ]
    )

    queue.reload()
    assert queue.attributes["ApproximateNumberOfMessages"] == "1"


@mock_aws
def test_change_message_visibility_on_old_message():
    sqs = boto3.resource("sqs", region_name=REGION)
    queue = sqs.create_queue(
        QueueName=str(uuid4())[0:6], Attributes={"VisibilityTimeout": "1"}
    )

    queue.send_message(MessageBody="test message 1")

    messages = queue.receive_messages(MaxNumberOfMessages=1)

    assert len(messages) == 1

    original_message = messages[0]

    queue.reload()
    assert queue.attributes["ApproximateNumberOfMessages"] == "0"

    time.sleep(2)

    queue.reload()
    assert queue.attributes["ApproximateNumberOfMessages"] == "1"

    messages = queue.receive_messages(MaxNumberOfMessages=1)

    assert len(messages) == 1

    # Docs indicate this should throw an ReceiptHandleIsInvalid, but this is allowed in AWS
    original_message.change_visibility(VisibilityTimeout=100)
    # Docs indicate this should throw a MessageNotInflight, but this is allowed in AWS
    original_message.change_visibility(VisibilityTimeout=100)

    time.sleep(2)

    # Message is not yet available, because of the visibility-timeout
    messages = queue.receive_messages(MaxNumberOfMessages=1)
    assert len(messages) == 0


@mock_aws
def test_change_message_visibility_on_visible_message():
    sqs = boto3.resource("sqs", region_name=REGION)
    queue = sqs.create_queue(
        QueueName=str(uuid4())[0:6], Attributes={"VisibilityTimeout": "2"}
    )

    queue.send_message(MessageBody="test message")
    messages = queue.receive_messages(MaxNumberOfMessages=1)
    assert len(messages) == 1

    queue.reload()
    assert queue.attributes["ApproximateNumberOfMessages"] == "0"

    time.sleep(2)

    messages = queue.receive_messages(MaxNumberOfMessages=1)
    assert len(messages) == 1

    messages[0].change_visibility(VisibilityTimeout=100)

    time.sleep(2)

    queue.reload()
    assert queue.attributes["ApproximateNumberOfMessages"] == "0"


@mock_aws
def test_purge_queue_before_delete_message():
    client = boto3.client("sqs", region_name=REGION)

    create_resp = client.create_queue(
        QueueName=f"dlr-{str(uuid4())[0:6]}.fifo", Attributes={"FifoQueue": "true"}
    )
    queue_url = create_resp["QueueUrl"]

    client.send_message(
        QueueUrl=queue_url,
        MessageGroupId="test",
        MessageDeduplicationId="first_message",
        MessageBody="first_message",
    )
    client.receive_message(QueueUrl=queue_url)

    # purge before call delete_message
    client.purge_queue(QueueUrl=queue_url)

    client.send_message(
        QueueUrl=queue_url,
        MessageGroupId="test",
        MessageDeduplicationId="second_message",
        MessageBody="second_message",
    )
    receive_resp2 = client.receive_message(QueueUrl=queue_url)

    assert len(receive_resp2.get("Messages", [])) == 1
    assert receive_resp2["Messages"][0]["Body"] == "second_message"


@mock_aws
def test_delete_message_after_visibility_timeout():
    VISIBILITY_TIMEOUT = 1
    sqs = boto3.resource("sqs", region_name=REGION)
    queue = sqs.create_queue(
        QueueName=str(uuid4())[0:6],
        Attributes={"VisibilityTimeout ": f"{VISIBILITY_TIMEOUT}"},
    )

    queue.send_message(MessageBody="Message 1!")

    queue.reload()
    assert queue.attributes["ApproximateNumberOfMessages"] == "1"

    m1_retrieved = queue.receive_messages()[0]

    time.sleep(VISIBILITY_TIMEOUT + 1)

    m1_retrieved.delete()

    queue.reload()
    assert queue.attributes["ApproximateNumberOfMessages"] == "0"


@mock_aws
def test_delete_message_errors():
    client = boto3.client("sqs", region_name=REGION)
    response = client.create_queue(QueueName=str(uuid4())[0:6])
    queue_url = response["QueueUrl"]
    client.send_message(QueueUrl=queue_url, MessageBody="body")
    response = client.receive_message(QueueUrl=queue_url)
    receipt_handle = response["Messages"][0]["ReceiptHandle"]

    with pytest.raises(ClientError) as client_error:
        client.delete_message(
            QueueUrl=queue_url + "-not-existing", ReceiptHandle=receipt_handle
        )
    assert client_error.value.response["Error"]["Message"] == (
        "The specified queue does not exist for this wsdl version."
    )

    with pytest.raises(ClientError) as client_error:
        client.delete_message(QueueUrl=queue_url, ReceiptHandle="not-existing")
    assert (
        client_error.value.response["Error"]["Message"]
        == "The input receipt handle is invalid."
    )


@mock_aws
def test_delete_message_twice_using_same_receipt_handle():
    client = boto3.client("sqs", region_name=REGION)
    response = client.create_queue(QueueName=str(uuid4())[0:6])
    queue_url = response["QueueUrl"]

    client.send_message(QueueUrl=queue_url, MessageBody="body")
    response = client.receive_message(QueueUrl=queue_url)
    receipt_handle = response["Messages"][0]["ReceiptHandle"]

    client.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)
    client.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)


@mock_aws
def test_delete_message_using_old_receipt_handle():
    client = boto3.client("sqs", region_name=REGION)
    response = client.create_queue(
        QueueName=str(uuid4())[0:6], Attributes={"VisibilityTimeout": "0"}
    )
    queue_url = response["QueueUrl"]

    client.send_message(QueueUrl=queue_url, MessageBody="body")
    response = client.receive_message(QueueUrl=queue_url)
    receipt_1 = response["Messages"][0]["ReceiptHandle"]

    response = client.receive_message(QueueUrl=queue_url)
    receipt_2 = response["Messages"][0]["ReceiptHandle"]

    assert receipt_1 != receipt_2

    # Can use an old receipt_handle to delete a message
    client.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_1)
    # Sanity check the message really is gone
    assert "Messages" not in client.receive_message(QueueUrl=queue_url)
    # We can delete it again
    client.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_1)

    # Can use the second receipt handle to delete it 'again' - succeeds,
    # as it is idempotent against the message
    client.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_2)


@mock_aws
def test_send_message_batch():
    client = boto3.client("sqs", region_name=REGION)
    response = client.create_queue(
        QueueName=f"{str(uuid4())[0:6]}.fifo", Attributes={"FifoQueue": "true"}
    )
    queue_url = response["QueueUrl"]

    response = client.send_message_batch(
        QueueUrl=queue_url,
        Entries=[
            {
                "Id": "id_1",
                "MessageBody": "body_1",
                "DelaySeconds": 0,
                "MessageAttributes": {
                    "attribute_name_1": {
                        "StringValue": "attribute_value_1",
                        "DataType": "String",
                    }
                },
                "MessageGroupId": "message_group_id_1",
                "MessageDeduplicationId": "message_deduplication_id_1",
            },
            {
                "Id": "id_2",
                "MessageBody": "body_2",
                "DelaySeconds": 0,
                "MessageAttributes": {
                    "attribute_name_2": {"StringValue": "123", "DataType": "Number"}
                },
                "MessageGroupId": "message_group_id_2",
                "MessageDeduplicationId": "message_deduplication_id_2",
            },
        ],
    )

    assert sorted([entry["Id"] for entry in response["Successful"]]) == ["id_1", "id_2"]

    response = client.receive_message(
        QueueUrl=queue_url,
        MaxNumberOfMessages=10,
        MessageAttributeNames=["attribute_name_1", "attribute_name_2"],
        AttributeNames=["MessageDeduplicationId", "MessageGroupId"],
    )

    assert response["Messages"][0]["Body"] == "body_1"
    assert response["Messages"][0]["MessageAttributes"] == (
        {"attribute_name_1": {"StringValue": "attribute_value_1", "DataType": "String"}}
    )
    assert (
        response["Messages"][0]["Attributes"]["MessageGroupId"] == "message_group_id_1"
    )
    assert response["Messages"][0]["Attributes"]["MessageDeduplicationId"] == (
        "message_deduplication_id_1"
    )
    assert response["Messages"][1]["Body"] == "body_2"
    assert response["Messages"][1]["MessageAttributes"] == (
        {"attribute_name_2": {"StringValue": "123", "DataType": "Number"}}
    )
    assert response["Messages"][1]["Attributes"]["MessageGroupId"] == (
        "message_group_id_2"
    )
    assert response["Messages"][1]["Attributes"]["MessageDeduplicationId"] == (
        "message_deduplication_id_2"
    )


@mock_aws
def test_delete_message_batch_with_duplicates():
    client = boto3.client("sqs", region_name=REGION)
    response = client.create_queue(QueueName=str(uuid4())[0:6])
    queue_url = response["QueueUrl"]
    client.send_message(QueueUrl=queue_url, MessageBody="coucou")

    messages = client.receive_message(
        QueueUrl=queue_url, WaitTimeSeconds=0, VisibilityTimeout=0
    )["Messages"]
    assert messages, "at least one msg"
    entries = [
        {"Id": msg["MessageId"], "ReceiptHandle": msg["ReceiptHandle"]}
        for msg in [messages[0], messages[0]]
    ]

    with pytest.raises(ClientError) as e:
        client.delete_message_batch(QueueUrl=queue_url, Entries=entries)
    ex = e.value
    assert ex.response["Error"]["Code"] == "BatchEntryIdsNotDistinct"

    # no messages are deleted
    messages = client.receive_message(QueueUrl=queue_url, WaitTimeSeconds=0).get(
        "Messages", []
    )
    assert messages, "message still in the queue"


@mock_aws
def test_delete_message_batch_with_invalid_receipt_id():
    client = boto3.client("sqs", region_name=REGION)
    response = client.create_queue(QueueName=str(uuid4())[0:6])
    queue_url = response["QueueUrl"]
    client.send_message(QueueUrl=queue_url, MessageBody="coucou")

    messages = client.receive_message(
        QueueUrl=queue_url, WaitTimeSeconds=0, VisibilityTimeout=0
    )["Messages"]
    assert messages, "at least one msg"

    # Try to delete the message from SQS but also include two invalid delete requests
    entries = [
        {"Id": "fake-receipt-handle-1", "ReceiptHandle": "fake-receipt-handle-1"},
        {"Id": messages[0]["MessageId"], "ReceiptHandle": messages[0]["ReceiptHandle"]},
        {"Id": "fake-receipt-handle-2", "ReceiptHandle": "fake-receipt-handle-2"},
    ]
    response = client.delete_message_batch(QueueUrl=queue_url, Entries=entries)

    assert response["Successful"] == [
        {"Id": messages[0]["MessageId"]}
    ], "delete ok for real message"

    assert response["Failed"] == [
        {
            "Id": "fake-receipt-handle-1",
            "SenderFault": True,
            "Code": "ReceiptHandleIsInvalid",
            "Message": (
                'The input receipt handle "fake-receipt-handle-1" is not '
                "a valid receipt handle."
            ),
        },
        {
            "Id": "fake-receipt-handle-2",
            "SenderFault": True,
            "Code": "ReceiptHandleIsInvalid",
            "Message": (
                'The input receipt handle "fake-receipt-handle-2" is not '
                "a valid receipt handle."
            ),
        },
    ]


@mock_aws
def test_message_attributes_in_receive_message():
    sqs = boto3.resource("sqs", region_name=REGION)
    conn = boto3.client("sqs", region_name=REGION)
    q_resp = conn.create_queue(QueueName=str(uuid4())[0:6])
    queue = sqs.Queue(q_resp["QueueUrl"])

    body_one = "this is a test message"

    queue.send_message(
        MessageBody=body_one,
        MessageAttributes={
            "timestamp": {
                "StringValue": "1493147359900",
                "DataType": "Number.java.lang.Long",
            }
        },
    )
    messages = conn.receive_message(
        QueueUrl=queue.url, MaxNumberOfMessages=2, MessageAttributeNames=["timestamp"]
    )["Messages"]

    assert messages[0]["MessageAttributes"] == {
        "timestamp": {
            "StringValue": "1493147359900",
            "DataType": "Number.java.lang.Long",
        }
    }

    queue.send_message(
        MessageBody=body_one,
        MessageAttributes={
            "timestamp": {
                "StringValue": "1493147359900",
                "DataType": "Number.java.lang.Long",
            }
        },
    )
    messages = conn.receive_message(QueueUrl=queue.url, MaxNumberOfMessages=2)[
        "Messages"
    ]

    assert messages[0].get("MessageAttributes") is None

    queue.send_message(
        MessageBody=body_one,
        MessageAttributes={
            "timestamp": {
                "StringValue": "1493147359900",
                "DataType": "Number.java.lang.Long",
            }
        },
    )
    messages = conn.receive_message(
        QueueUrl=queue.url, MaxNumberOfMessages=2, MessageAttributeNames=["All"]
    )["Messages"]

    assert messages[0]["MessageAttributes"] == {
        "timestamp": {
            "StringValue": "1493147359900",
            "DataType": "Number.java.lang.Long",
        }
    }


@mock_aws
def test_send_message_batch_errors():
    client = boto3.client("sqs", region_name=REGION)

    response = client.create_queue(QueueName="test-queue")
    queue_url = response["QueueUrl"]

    with pytest.raises(ClientError) as client_error:
        client.send_message_batch(
            QueueUrl=queue_url + "-not-existing",
            Entries=[{"Id": "id_1", "MessageBody": "body_1"}],
        )
    assert client_error.value.response["Error"]["Message"] == (
        "The specified queue does not exist for this wsdl version."
    )

    with pytest.raises(ClientError) as client_error:
        client.send_message_batch(QueueUrl=queue_url, Entries=[])
    assert client_error.value.response["Error"]["Message"] == (
        "There should be at least one SendMessageBatchRequestEntry in the request."
    )

    with pytest.raises(ClientError) as client_error:
        client.send_message_batch(
            QueueUrl=queue_url, Entries=[{"Id": "", "MessageBody": "body_1"}]
        )
    assert client_error.value.response["Error"]["Message"] == (
        "A batch entry id can only contain alphanumeric characters, "
        "hyphens and underscores. It can be at most 80 letters long."
    )

    with pytest.raises(ClientError) as client_error:
        client.send_message_batch(
            QueueUrl=queue_url,
            Entries=[{"Id": ".!@#$%^&*()+=", "MessageBody": "body_1"}],
        )
    assert client_error.value.response["Error"]["Message"] == (
        "A batch entry id can only contain alphanumeric characters, "
        "hyphens and underscores. It can be at most 80 letters long."
    )

    with pytest.raises(ClientError) as client_error:
        client.send_message_batch(
            QueueUrl=queue_url, Entries=[{"Id": "i" * 81, "MessageBody": "body_1"}]
        )
    assert client_error.value.response["Error"]["Message"] == (
        "A batch entry id can only contain alphanumeric characters, "
        "hyphens and underscores. It can be at most 80 letters long."
    )

    with pytest.raises(ClientError) as client_error:
        client.send_message_batch(
            QueueUrl=queue_url, Entries=[{"Id": "id_1", "MessageBody": "b" * 262145}]
        )
    assert client_error.value.response["Error"]["Message"] == (
        "Batch requests cannot be longer than 262144 bytes. "
        "You have sent 262145 bytes."
    )

    with pytest.raises(ClientError) as client_error:
        # only the first duplicated Id is reported
        client.send_message_batch(
            QueueUrl=queue_url,
            Entries=[
                {"Id": "id_1", "MessageBody": "body_1"},
                {"Id": "id_2", "MessageBody": "body_2"},
                {"Id": "id_2", "MessageBody": "body_2"},
                {"Id": "id_1", "MessageBody": "body_1"},
            ],
        )
    assert client_error.value.response["Error"]["Message"] == "Id id_2 repeated."

    entries = [{"Id": f"id_{i}", "MessageBody": f"body_{i}"} for i in range(11)]
    with pytest.raises(ClientError) as client_error:
        assert client.send_message_batch(QueueUrl=queue_url, Entries=entries)
    assert client_error.value.response["Error"]["Message"] == (
        "Maximum number of entries per request are 10. You have sent 11."
    )


@mock_aws
def test_send_message_batch_with_empty_list():
    client = boto3.client("sqs", region_name=REGION)

    response = client.create_queue(QueueName="test-queue")
    queue_url = response["QueueUrl"]

    with pytest.raises(ClientError) as client_error:
        client.send_message_batch(QueueUrl=queue_url, Entries=[])
    assert client_error.value.response["Error"]["Message"] == (
        "There should be at least one SendMessageBatchRequestEntry in the request."
    )


@mock_aws
def test_batch_change_message_visibility():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Cant manipulate time in server mode")

    with freeze_time("2015-01-01 12:00:00"):
        sqs = boto3.client("sqs", region_name=REGION)
        resp = sqs.create_queue(
            QueueName="test-dlr-queue.fifo",
            Attributes={"FifoQueue": "true", "ContentBasedDeduplication": "true"},
        )
        queue_url = resp["QueueUrl"]

        sqs.send_message(
            QueueUrl=queue_url, MessageBody="msg1", MessageGroupId="group1"
        )
        sqs.send_message(
            QueueUrl=queue_url, MessageBody="msg2", MessageGroupId="group2"
        )
        sqs.send_message(
            QueueUrl=queue_url, MessageBody="msg3", MessageGroupId="group3"
        )

    with freeze_time("2015-01-01 12:01:00"):
        receive_resp = sqs.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=2)
        assert len(receive_resp["Messages"]) == 2

        handles = [item["ReceiptHandle"] for item in receive_resp["Messages"]]
        entries = [
            {
                "Id": str(uuid4()),
                "ReceiptHandle": handle,
                "VisibilityTimeout": 43000,
            }
            for handle in handles
        ]

        resp = sqs.change_message_visibility_batch(QueueUrl=queue_url, Entries=entries)
        assert len(resp["Successful"]) == 2

    with freeze_time("2015-01-01 14:00:00"):
        resp = sqs.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=3)
        assert len(resp["Messages"]) == 1

    with freeze_time("2015-01-01 16:00:00"):
        resp = sqs.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=3)
        assert len(resp["Messages"]) == 1

    with freeze_time("2015-01-02 12:00:00"):
        resp = sqs.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=3)
        assert len(resp["Messages"]) == 3


@mock_aws
def test_batch_change_message_visibility_on_old_message():
    sqs = boto3.resource("sqs", region_name=REGION)
    queue = sqs.create_queue(
        QueueName=str(uuid4())[0:6], Attributes={"VisibilityTimeout": "1"}
    )

    queue.send_message(MessageBody="test message 1")

    messages = queue.receive_messages(MaxNumberOfMessages=1)

    assert len(messages) == 1

    original_message = messages[0]

    time.sleep(2)

    messages = queue.receive_messages(MaxNumberOfMessages=1)
    assert messages[0].receipt_handle != original_message.receipt_handle

    entries = [
        {
            "Id": str(uuid4()),
            "ReceiptHandle": original_message.receipt_handle,
            "VisibilityTimeout": 4,
        }
    ]

    resp = queue.change_message_visibility_batch(Entries=entries)
    assert len(resp["Successful"]) == 1


@mock_aws
def test_permissions():
    client = boto3.client("sqs", region_name=REGION)

    q_name = f"{str(uuid4())[0:6]}.fifo"
    resp = client.create_queue(QueueName=q_name, Attributes={"FifoQueue": "true"})
    queue_url = resp["QueueUrl"]

    client.add_permission(
        QueueUrl=queue_url,
        Label="account1",
        AWSAccountIds=["111111111111"],
        Actions=["*"],
    )
    client.add_permission(
        QueueUrl=queue_url,
        Label="account2",
        AWSAccountIds=["222211111111"],
        Actions=["SendMessage"],
    )

    response = client.get_queue_attributes(
        QueueUrl=queue_url, AttributeNames=["Policy"]
    )
    policy = json.loads(response["Attributes"]["Policy"])
    assert policy["Version"] == "2012-10-17"
    assert policy["Id"] == (
        f"arn:aws:sqs:{REGION}:123456789012:{q_name}/SQSDefaultPolicy"
    )
    assert sorted(policy["Statement"], key=lambda x: x["Sid"]) == [
        {
            "Sid": "account1",
            "Effect": "Allow",
            "Principal": {"AWS": "arn:aws:iam::111111111111:root"},
            "Action": "SQS:*",
            "Resource": f"arn:aws:sqs:{REGION}:123456789012:{q_name}",
        },
        {
            "Sid": "account2",
            "Effect": "Allow",
            "Principal": {"AWS": "arn:aws:iam::222211111111:root"},
            "Action": "SQS:SendMessage",
            "Resource": f"arn:aws:sqs:{REGION}:123456789012:{q_name}",
        },
    ]

    client.remove_permission(QueueUrl=queue_url, Label="account2")

    response = client.get_queue_attributes(
        QueueUrl=queue_url, AttributeNames=["Policy"]
    )
    assert json.loads(response["Attributes"]["Policy"]) == {
        "Version": "2012-10-17",
        "Id": f"arn:aws:sqs:{REGION}:123456789012:{q_name}/SQSDefaultPolicy",
        "Statement": [
            {
                "Sid": "account1",
                "Effect": "Allow",
                "Principal": {"AWS": "arn:aws:iam::111111111111:root"},
                "Action": "SQS:*",
                "Resource": f"arn:aws:sqs:{REGION}:123456789012:{q_name}",
            },
        ],
    }


@mock_aws
def test_get_queue_attributes_template_response_validation():
    client = boto3.client("sqs", region_name=REGION)

    resp = client.create_queue(
        QueueName=f"{str(uuid4())[0:6]}.fifo", Attributes={"FifoQueue": "true"}
    )
    queue_url = resp["QueueUrl"]

    attrs = client.get_queue_attributes(QueueUrl=queue_url, AttributeNames=["All"])
    assert attrs.get("Attributes").get("Policy") is None

    attributes = {"Policy": TEST_POLICY}

    client.set_queue_attributes(QueueUrl=queue_url, Attributes=attributes)
    attrs = client.get_queue_attributes(QueueUrl=queue_url, AttributeNames=["Policy"])
    assert attrs.get("Attributes").get("Policy") is not None

    assert (
        json.loads(attrs.get("Attributes").get("Policy")).get("Version") == "2012-10-17"
    )
    assert len(json.loads(attrs.get("Attributes").get("Policy")).get("Statement")) == 1
    assert (
        json.loads(attrs.get("Attributes").get("Policy"))
        .get("Statement")[0]
        .get("Action")
        == "sqs:SendMessage"
    )


@mock_aws
def test_add_permission_errors():
    client = boto3.client("sqs", region_name=REGION)
    response = client.create_queue(QueueName=str(uuid4())[0:6])
    queue_url = response["QueueUrl"]
    client.add_permission(
        QueueUrl=queue_url,
        Label="test",
        AWSAccountIds=["111111111111"],
        Actions=["ReceiveMessage"],
    )

    with pytest.raises(ClientError) as e:
        client.add_permission(
            QueueUrl=queue_url,
            Label="test",
            AWSAccountIds=["111111111111"],
            Actions=["ReceiveMessage", "SendMessage"],
        )
    ex = e.value
    assert ex.operation_name == "AddPermission"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "InvalidParameterValue" in ex.response["Error"]["Code"]
    assert ex.response["Error"]["Message"] == (
        "Value test for parameter Label is invalid. Reason: Already exists."
    )

    with pytest.raises(ClientError) as e:
        client.add_permission(
            QueueUrl=queue_url,
            Label="test-2",
            AWSAccountIds=["111111111111"],
            Actions=["RemovePermission"],
        )
    ex = e.value
    assert ex.operation_name == "AddPermission"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "InvalidParameterValue" in ex.response["Error"]["Code"]
    assert ex.response["Error"]["Message"] == (
        "Value SQS:RemovePermission for parameter ActionName is invalid. "
        "Reason: Only the queue owner is allowed to invoke this action."
    )

    with pytest.raises(ClientError) as e:
        client.add_permission(
            QueueUrl=queue_url,
            Label="test-2",
            AWSAccountIds=["111111111111"],
            Actions=[],
        )
    ex = e.value
    assert ex.operation_name == "AddPermission"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "MissingParameter" in ex.response["Error"]["Code"]
    assert ex.response["Error"]["Message"] == (
        "The request must contain the parameter Actions."
    )

    with pytest.raises(ClientError) as e:
        client.add_permission(
            QueueUrl=queue_url,
            Label="test-2",
            AWSAccountIds=[],
            Actions=["ReceiveMessage"],
        )
    ex = e.value
    assert ex.operation_name == "AddPermission"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "InvalidParameterValue" in ex.response["Error"]["Code"]
    assert ex.response["Error"]["Message"] == (
        "Value [] for parameter PrincipalId is invalid. Reason: Unable to verify."
    )

    with pytest.raises(ClientError) as e:
        client.add_permission(
            QueueUrl=queue_url,
            Label="test-2",
            AWSAccountIds=["111111111111"],
            Actions=[
                "ChangeMessageVisibility",
                "DeleteMessage",
                "GetQueueAttributes",
                "GetQueueUrl",
                "ListDeadLetterSourceQueues",
                "PurgeQueue",
                "ReceiveMessage",
                "SendMessage",
            ],
        )
    ex = e.value
    assert ex.operation_name == "AddPermission"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 403
    assert "OverLimit" in ex.response["Error"]["Code"]
    assert ex.response["Error"]["Message"] == (
        "8 Actions were found, maximum allowed is 7."
    )


@mock_aws
def test_remove_permission_errors():
    client = boto3.client("sqs", region_name=REGION)
    response = client.create_queue(QueueName=str(uuid4())[0:6])
    queue_url = response["QueueUrl"]

    with pytest.raises(ClientError) as e:
        client.remove_permission(QueueUrl=queue_url, Label="test")
    ex = e.value
    assert ex.operation_name == "RemovePermission"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "InvalidParameterValue" in ex.response["Error"]["Code"]
    assert ex.response["Error"]["Message"] == (
        "Value test for parameter Label is invalid. "
        "Reason: can't find label on existing policy."
    )


@mock_aws
def test_tags():
    client = boto3.client("sqs", region_name=REGION)

    resp = client.create_queue(
        QueueName="test-dlr-queue.fifo", Attributes={"FifoQueue": "true"}
    )
    queue_url = resp["QueueUrl"]

    client.tag_queue(QueueUrl=queue_url, Tags={"test1": "value1", "test2": "value2"})

    resp = client.list_queue_tags(QueueUrl=queue_url)
    assert "test1" in resp["Tags"]
    assert "test2" in resp["Tags"]

    client.untag_queue(QueueUrl=queue_url, TagKeys=["test2"])

    resp = client.list_queue_tags(QueueUrl=queue_url)
    assert "test1" in resp["Tags"]
    assert "test2" not in resp["Tags"]

    # removing a non existing tag should not raise any error
    client.untag_queue(QueueUrl=queue_url, TagKeys=["not-existing-tag"])
    assert client.list_queue_tags(QueueUrl=queue_url)["Tags"] == {"test1": "value1"}


@mock_aws
def test_list_queue_tags_errors():
    client = boto3.client("sqs", region_name=REGION)

    response = client.create_queue(
        QueueName=str(uuid4())[0:6], tags={"tag_key_1": "tag_value_X"}
    )
    queue_url = response["QueueUrl"]

    with pytest.raises(ClientError) as client_error:
        client.list_queue_tags(QueueUrl=queue_url + "-not-existing")
    assert client_error.value.response["Error"]["Message"] == (
        "The specified queue does not exist for this wsdl version."
    )


@mock_aws
def test_tag_queue_errors():
    client = boto3.client("sqs", region_name=REGION)

    q_name = str(uuid4())[0:6]
    response = client.create_queue(QueueName=q_name, tags={"tag_key_1": "tag_value_X"})
    queue_url = response["QueueUrl"]

    with pytest.raises(ClientError) as client_error:
        client.tag_queue(
            QueueUrl=queue_url + "-not-existing", Tags={"tag_key_1": "tag_value_1"}
        )
    assert client_error.value.response["Error"]["Message"] == (
        "The specified queue does not exist for this wsdl version."
    )

    with pytest.raises(ClientError) as client_error:
        client.tag_queue(QueueUrl=queue_url, Tags={})
    assert client_error.value.response["Error"]["Message"] == (
        "The request must contain the parameter Tags."
    )

    too_many_tags = {f"tag_key_{i}": f"tag_value_{i}" for i in range(51)}
    with pytest.raises(ClientError) as client_error:
        client.tag_queue(QueueUrl=queue_url, Tags=too_many_tags)
    assert client_error.value.response["Error"]["Message"] == (
        f"Too many tags added for queue {q_name}."
    )

    # when the request fails, the tags should not be updated
    assert client.list_queue_tags(QueueUrl=queue_url)["Tags"] == (
        {"tag_key_1": "tag_value_X"}
    )


@mock_aws
def test_untag_queue_errors():
    client = boto3.client("sqs", region_name=REGION)

    response = client.create_queue(
        QueueName=str(uuid4())[0:6], tags={"tag_key_1": "tag_value_1"}
    )
    queue_url = response["QueueUrl"]

    with pytest.raises(ClientError) as client_error:
        client.untag_queue(QueueUrl=queue_url + "-not-existing", TagKeys=["tag_key_1"])
    assert client_error.value.response["Error"]["Message"] == (
        "The specified queue does not exist for this wsdl version."
    )

    with pytest.raises(ClientError) as client_error:
        client.untag_queue(QueueUrl=queue_url, TagKeys=[])
    assert client_error.value.response["Error"]["Message"] == (
        "Tag keys must be between 1 and 128 characters in length."
    )


@mock_aws
def test_create_fifo_queue_with_dlq():
    sqs = boto3.client("sqs", region_name=REGION)
    resp = sqs.create_queue(
        QueueName=f"{str(uuid4())[0:6]}.fifo", Attributes={"FifoQueue": "true"}
    )
    queue_url1 = resp["QueueUrl"]
    queue_arn1 = sqs.get_queue_attributes(
        QueueUrl=queue_url1, AttributeNames=["QueueArn"]
    )["Attributes"]["QueueArn"]

    resp = sqs.create_queue(
        QueueName=str(uuid4())[0:6], Attributes={"FifoQueue": "false"}
    )
    queue_url2 = resp["QueueUrl"]
    queue_arn2 = sqs.get_queue_attributes(
        QueueUrl=queue_url2, AttributeNames=["QueueArn"]
    )["Attributes"]["QueueArn"]

    sqs.create_queue(
        QueueName=f"{str(uuid4())[0:6]}.fifo",
        Attributes={
            "FifoQueue": "true",
            "RedrivePolicy": json.dumps(
                {"deadLetterTargetArn": queue_arn1, "maxReceiveCount": 2}
            ),
        },
    )

    # Cant have fifo queue with non fifo DLQ
    with pytest.raises(ClientError):
        sqs.create_queue(
            QueueName=f"{str(uuid4())[0:6]}.fifo",
            Attributes={
                "FifoQueue": "true",
                "RedrivePolicy": json.dumps(
                    {"deadLetterTargetArn": queue_arn2, "maxReceiveCount": 2}
                ),
            },
        )


@mock_aws
def test_queue_with_dlq():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Cant manipulate time in server mode")

    sqs = boto3.client("sqs", region_name=REGION)

    with freeze_time("2015-01-01 12:00:00"):
        resp = sqs.create_queue(
            QueueName=f"{str(uuid4())[0:6]}.fifo",
            Attributes={"FifoQueue": "true", "ContentBasedDeduplication": "true"},
        )
        queue_url1 = resp["QueueUrl"]
        queue_arn1 = sqs.get_queue_attributes(
            QueueUrl=queue_url1, AttributeNames=["QueueArn"]
        )["Attributes"]["QueueArn"]

        resp = sqs.create_queue(
            QueueName=f"{str(uuid4())[0:6]}.fifo",
            Attributes={
                "FifoQueue": "true",
                "ContentBasedDeduplication": "true",
                "RedrivePolicy": json.dumps(
                    {"deadLetterTargetArn": queue_arn1, "maxReceiveCount": 2}
                ),
            },
        )
        queue_url2 = resp["QueueUrl"]

        sqs.send_message(
            QueueUrl=queue_url2, MessageBody="msg1", MessageGroupId="group"
        )
        sqs.send_message(
            QueueUrl=queue_url2, MessageBody="msg2", MessageGroupId="group"
        )

    with freeze_time("2015-01-01 13:00:00"):
        resp = sqs.receive_message(
            QueueUrl=queue_url2, VisibilityTimeout=30, WaitTimeSeconds=0
        )
        assert resp["Messages"][0]["Body"] == "msg1"

    with freeze_time("2015-01-01 13:01:00"):
        resp = sqs.receive_message(
            QueueUrl=queue_url2, VisibilityTimeout=30, WaitTimeSeconds=0
        )
        assert resp["Messages"][0]["Body"] == "msg1"

    with freeze_time("2015-01-01 13:02:00"):
        resp = sqs.receive_message(
            QueueUrl=queue_url2, VisibilityTimeout=30, WaitTimeSeconds=0
        )
        assert len(resp["Messages"]) == 1

    with freeze_time("2015-01-01 13:02:00"):
        resp = sqs.receive_message(
            QueueUrl=queue_url1, VisibilityTimeout=30, WaitTimeSeconds=0
        )
        assert resp["Messages"][0]["Body"] == "msg1"

    # Might as well test list source queues

    resp = sqs.list_dead_letter_source_queues(QueueUrl=queue_url1)
    assert resp["queueUrls"][0] == queue_url2


@mock_aws
def test_redrive_policy_available():
    sqs = boto3.client("sqs", region_name=REGION)

    resp = sqs.create_queue(QueueName=str(uuid4())[0:6])
    queue_url1 = resp["QueueUrl"]
    queue_arn1 = sqs.get_queue_attributes(
        QueueUrl=queue_url1, AttributeNames=["QueueArn"]
    )["Attributes"]["QueueArn"]
    redrive_policy = {"deadLetterTargetArn": queue_arn1, "maxReceiveCount": 1}

    resp = sqs.create_queue(
        QueueName=str(uuid4())[0:6],
        Attributes={"RedrivePolicy": json.dumps(redrive_policy)},
    )

    queue_url2 = resp["QueueUrl"]
    attributes = sqs.get_queue_attributes(
        QueueUrl=queue_url2, AttributeNames=["RedrivePolicy"]
    )["Attributes"]
    assert "RedrivePolicy" in attributes
    assert json.loads(attributes["RedrivePolicy"]) == redrive_policy

    # Cant have redrive policy without maxReceiveCount
    with pytest.raises(ClientError):
        sqs.create_queue(
            QueueName=str(uuid4())[0:6],
            Attributes={
                "FifoQueue": "true",
                "RedrivePolicy": json.dumps({"deadLetterTargetArn": queue_arn1}),
            },
        )


@mock_aws
def test_redrive_policy_non_existent_queue():
    sqs = boto3.client("sqs", region_name=REGION)
    redrive_policy = {
        "deadLetterTargetArn": f"arn:aws:sqs:{REGION}:{ACCOUNT_ID}:no-queue",
        "maxReceiveCount": 1,
    }

    with pytest.raises(ClientError):
        sqs.create_queue(
            QueueName="test-queue",
            Attributes={"RedrivePolicy": json.dumps(redrive_policy)},
        )


@mock_aws
def test_redrive_policy_set_attributes():
    sqs = boto3.resource("sqs", region_name=REGION)

    q_name = str(uuid4())[0:6]
    queue = sqs.create_queue(QueueName=q_name)
    deadletter_queue = sqs.create_queue(QueueName=str(uuid4())[0:6])

    redrive_policy = {
        "deadLetterTargetArn": deadletter_queue.attributes["QueueArn"],
        "maxReceiveCount": 1,
    }

    queue.set_attributes(Attributes={"RedrivePolicy": json.dumps(redrive_policy)})

    copy = sqs.get_queue_by_name(QueueName=q_name)
    assert "RedrivePolicy" in copy.attributes
    copy_policy = json.loads(copy.attributes["RedrivePolicy"])
    assert copy_policy == redrive_policy


@mock_aws
def test_redrive_policy_set_attributes_with_string_value():
    sqs = boto3.resource("sqs", region_name=REGION)

    q_name = str(uuid4())[0:6]
    queue = sqs.create_queue(QueueName=q_name)
    deadletter_queue = sqs.create_queue(QueueName=str(uuid4())[0:6])

    queue.set_attributes(
        Attributes={
            "RedrivePolicy": json.dumps(
                {
                    "deadLetterTargetArn": deadletter_queue.attributes["QueueArn"],
                    "maxReceiveCount": "1",
                }
            )
        }
    )

    copy = sqs.get_queue_by_name(QueueName=q_name)
    assert "RedrivePolicy" in copy.attributes
    copy_policy = json.loads(copy.attributes["RedrivePolicy"])
    assert copy_policy == {
        "deadLetterTargetArn": deadletter_queue.attributes["QueueArn"],
        "maxReceiveCount": 1,
    }


@mock_aws
def test_receive_messages_with_message_group_id():
    sqs = boto3.resource("sqs", region_name=REGION)
    queue = sqs.create_queue(
        QueueName=f"{str(uuid4())[0:6]}.fifo",
        Attributes={"FifoQueue": "true", "ContentBasedDeduplication": "true"},
    )
    queue.set_attributes(Attributes={"VisibilityTimeout": "3600"})
    queue.send_message(MessageBody="message-1", MessageGroupId="group")
    queue.send_message(MessageBody="message-2", MessageGroupId="group")
    queue.send_message(MessageBody="message-3", MessageGroupId="group")
    queue.send_message(MessageBody="separate-message", MessageGroupId="anothergroup")

    messages = queue.receive_messages(
        MaxNumberOfMessages=2, AttributeNames=["MessageGroupId"]
    )
    assert len(messages) == 2
    assert messages[0].attributes["MessageGroupId"] == "group"

    # Different client can not 'see' messages from the group until they are processed
    messages_for_client_2 = queue.receive_messages(WaitTimeSeconds=0)
    assert len(messages_for_client_2) == 1
    assert messages_for_client_2[0].body == "separate-message"

    # message is now processed, next one should be available
    for message in messages:
        message.delete()
    messages = queue.receive_messages()
    assert len(messages) == 1
    assert messages[0].body == "message-3"


@mock_aws
def test_receive_messages_with_message_group_id_on_requeue():
    sqs = boto3.resource("sqs", region_name=REGION)
    queue = sqs.create_queue(
        QueueName=f"{str(uuid4())[0:6]}.fifo",
        Attributes={"FifoQueue": "true", "ContentBasedDeduplication": "true"},
    )
    queue.set_attributes(Attributes={"VisibilityTimeout": "3600"})
    queue.send_message(MessageBody="message-1", MessageGroupId="group")
    queue.send_message(MessageBody="message-2", MessageGroupId="group")

    messages = queue.receive_messages()
    assert len(messages) == 1
    message = messages[0]

    # received message is not deleted!

    messages = queue.receive_messages(WaitTimeSeconds=0)
    assert len(messages) == 0

    # message is now available again, next one should be available
    message.change_visibility(VisibilityTimeout=0)
    messages = queue.receive_messages()
    assert len(messages) == 1
    assert messages[0].message_id == message.message_id


@mock_aws
def test_receive_messages_with_message_group_id_on_visibility_timeout():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Cant manipulate time in server mode")

    with freeze_time("2015-01-01 12:00:00"):
        sqs = boto3.resource("sqs", region_name=REGION)
        queue = sqs.create_queue(
            QueueName="test-queue.fifo",
            Attributes={"FifoQueue": "true", "ContentBasedDeduplication": "true"},
        )
        queue.set_attributes(Attributes={"VisibilityTimeout": "3600"})
        queue.send_message(MessageBody="message-1", MessageGroupId="group")
        queue.send_message(MessageBody="message-2", MessageGroupId="group")

        messages = queue.receive_messages()
        assert len(messages) == 1
        message = messages[0]

        # received message is not processed yet
        messages_for_second_client = queue.receive_messages(WaitTimeSeconds=0)
        assert len(messages_for_second_client) == 0

        for message in messages:
            message.change_visibility(VisibilityTimeout=10)

    with freeze_time("2015-01-01 12:00:05"):
        # no timeout yet
        messages = queue.receive_messages(WaitTimeSeconds=0)
        assert len(messages) == 0

    with freeze_time("2015-01-01 12:00:15"):
        # message is now available again, next one should be available
        messages = queue.receive_messages()
        assert len(messages) == 1
        assert messages[0].message_id == message.message_id


@mock_aws
def test_receive_message_for_queue_with_receive_message_wait_time_seconds_set():
    sqs = boto3.resource("sqs", region_name=REGION)

    queue = sqs.create_queue(
        QueueName=str(uuid4())[0:6], Attributes={"ReceiveMessageWaitTimeSeconds": "2"}
    )

    queue.receive_messages()


@mock_aws
def test_list_queues_limits_to_1000_queues():
    if settings.TEST_SERVER_MODE:
        # Re-visit once we have a NextToken-implementation for list_queues
        raise SkipTest("Too many queues for a persistent mode")
    client = boto3.client("sqs", region_name=REGION)

    prefix_name = str(uuid4())[0:6]
    queue_urls = []
    for i in range(1001):
        queue = client.create_queue(QueueName=f"{prefix_name}-{i}")
        queue_urls.append(queue["QueueUrl"])

    assert len(client.list_queues()["QueueUrls"]) == 1000
    assert len(client.list_queues(QueueNamePrefix=prefix_name)["QueueUrls"]) == 1000

    resource = boto3.resource("sqs", region_name=REGION)

    assert len(list(resource.queues.all())) == 1000
    assert len(list(resource.queues.filter(QueueNamePrefix=prefix_name))) == 1000

    # Delete this again, to not hog all the resources
    for url in queue_urls:
        client.delete_queue(QueueUrl=url)


@mock_aws
def test_send_message_to_fifo_without_message_group_id():
    sqs = boto3.resource("sqs", region_name="eu-west-3")
    queue = sqs.create_queue(
        QueueName=f"{str(uuid4())[0:6]}.fifo",
        Attributes={"FifoQueue": "true", "ContentBasedDeduplication": "true"},
    )

    with pytest.raises(ClientError) as exc:
        queue.send_message(MessageBody="message-1")
    err = exc.value.response["Error"]
    assert err["Code"] == "MissingParameter"
    assert err["Message"] == "The request must contain the parameter MessageGroupId."


@mock_aws
def test_send_messages_to_fifo_without_message_group_id():
    sqs = boto3.resource("sqs", region_name=REGION)
    queue = sqs.create_queue(
        QueueName=f"{str(uuid4())[0:6]}.fifo",
        Attributes={"FifoQueue": "true", "ContentBasedDeduplication": "true"},
    )

    with pytest.raises(ClientError) as exc:
        queue.send_messages(Entries=[{"Id": "id_1", "MessageBody": "body_1"}])
    err = exc.value.response["Error"]
    assert err["Code"] == "MissingParameter"
    assert err["Message"] == "The request must contain the parameter MessageGroupId."


@mock_aws
def test_maximum_message_size_attribute_default():
    sqs = boto3.resource("sqs", region_name="eu-west-3")
    queue = sqs.create_queue(QueueName=str(uuid4()))
    assert int(queue.attributes["MaximumMessageSize"]) == MAXIMUM_MESSAGE_LENGTH
    with pytest.raises(ClientError) as exc:
        queue.send_message(MessageBody="a" * (MAXIMUM_MESSAGE_LENGTH + 1))
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"


@mock_aws
def test_maximum_message_size_attribute_fails_for_invalid_values():
    sqs = boto3.resource("sqs", region_name="eu-west-3")
    invalid_values = [
        MAXIMUM_MESSAGE_SIZE_ATTR_LOWER_BOUND - 1,
        MAXIMUM_MESSAGE_SIZE_ATTR_UPPER_BOUND + 1,
    ]
    for message_size in invalid_values:
        with pytest.raises(ClientError) as e:
            sqs.create_queue(
                QueueName=str(uuid4()),
                Attributes={"MaximumMessageSize": str(message_size)},
            )
        ex = e.value
        assert ex.response["Error"]["Code"] == "InvalidAttributeValue"


@mock_aws
def test_send_message_fails_when_message_size_greater_than_max_message_size():
    sqs = boto3.resource("sqs", region_name="eu-west-3")
    message_size_limit = 12345
    queue = sqs.create_queue(
        QueueName=str(uuid4()),
        Attributes={"MaximumMessageSize": str(message_size_limit)},
    )
    assert int(queue.attributes["MaximumMessageSize"]) == message_size_limit
    with pytest.raises(ClientError) as e:
        queue.send_message(MessageBody="a" * (message_size_limit + 1))
    ex = e.value
    assert ex.response["Error"]["Code"] == "InvalidParameterValue"
    assert f"{message_size_limit} bytes" in ex.response["Error"]["Message"]


@mock_aws
@pytest.mark.parametrize(
    "msg_1, msg_2, dedupid_1, dedupid_2, expected_count",
    [
        ("msg1", "msg1", "1", "1", 1),
        ("msg1", "msg1", "1", "2", 2),
        ("msg1", "msg2", "1", "1", 1),
        ("msg1", "msg2", "1", "2", 2),
    ],
)
def test_fifo_queue_deduplication_with_id(
    msg_1, msg_2, dedupid_1, dedupid_2, expected_count
):
    sqs = boto3.resource("sqs", region_name=REGION)
    q_name = str(uuid4())[0:6]
    msg_queue = sqs.create_queue(
        QueueName=(f"{q_name}-dlq.fifo"),
        Attributes={"FifoQueue": "true", "ContentBasedDeduplication": "true"},
    )

    msg_queue.send_message(
        MessageBody=msg_1, MessageDeduplicationId=dedupid_1, MessageGroupId="1"
    )
    msg_queue.send_message(
        MessageBody=msg_2, MessageDeduplicationId=dedupid_2, MessageGroupId="2"
    )
    messages = msg_queue.receive_messages(MaxNumberOfMessages=2)
    assert len(messages) == expected_count


@mock_aws
@pytest.mark.parametrize(
    "msg_1, msg_2, expected_count", [("msg1", "msg1", 1), ("msg1", "msg2", 2)]
)
def test_fifo_queue_deduplication_withoutid(msg_1, msg_2, expected_count):
    sqs = boto3.resource("sqs", region_name=REGION)
    q_name = str(uuid4())[0:6]
    msg_queue = sqs.create_queue(
        QueueName=f"{q_name}-dlq.fifo",
        Attributes={"FifoQueue": "true", "ContentBasedDeduplication": "true"},
    )

    msg_queue.send_message(MessageBody=msg_1, MessageGroupId="1")
    msg_queue.send_message(MessageBody=msg_2, MessageGroupId="2")
    messages = msg_queue.receive_messages(MaxNumberOfMessages=2)
    assert len(messages) == expected_count


@mock.patch(
    "moto.sqs.models.DEDUPLICATION_TIME_IN_SECONDS", MOCK_DEDUPLICATION_TIME_IN_SECONDS
)
@mock_aws
def test_fifo_queue_send_duplicate_messages_after_deduplication_time_limit():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Cant patch env variables in server mode")

    sqs = boto3.resource("sqs", region_name=REGION)
    msg_queue = sqs.create_queue(
        QueueName="test-queue-dlq.fifo",
        Attributes={"FifoQueue": "true", "ContentBasedDeduplication": "true"},
    )

    msg_queue.send_message(MessageBody="first", MessageGroupId="1")
    time.sleep(MOCK_DEDUPLICATION_TIME_IN_SECONDS + 5)
    msg_queue.send_message(MessageBody="first", MessageGroupId="2")
    messages = msg_queue.receive_messages(MaxNumberOfMessages=2)
    assert len(messages) == 2


@mock_aws
def test_fifo_queue_send_deduplicationid_same_as_sha256_of_old_message():
    sqs = boto3.resource("sqs", region_name=REGION)
    q_name = str(uuid4())[0:6]
    msg_queue = sqs.create_queue(
        QueueName=f"{q_name}-dlq.fifo",
        Attributes={"FifoQueue": "true", "ContentBasedDeduplication": "true"},
    )

    msg_queue.send_message(MessageBody="first", MessageGroupId="1")

    sha256 = hashlib.sha256()
    sha256.update("first".encode("utf-8"))
    deduplicationid = sha256.hexdigest()

    msg_queue.send_message(
        MessageBody="second", MessageGroupId="2", MessageDeduplicationId=deduplicationid
    )
    messages = msg_queue.receive_messages(MaxNumberOfMessages=2)
    assert len(messages) == 1


@mock_aws
def test_fifo_send_message_when_same_group_id_is_in_dlq():
    sqs = boto3.resource("sqs", region_name=REGION)
    q_name = f"{str(uuid4())[0:6]}-dlq.fifo"
    dlq = sqs.create_queue(
        QueueName=q_name,
        Attributes={"FifoQueue": "true", "ContentBasedDeduplication": "true"},
    )

    queue = sqs.get_queue_by_name(QueueName=q_name)
    dead_letter_queue_arn = queue.attributes.get("QueueArn")

    msg_queue = sqs.create_queue(
        QueueName=f"{str(uuid4())[0:6]}.fifo",
        Attributes={
            "FifoQueue": "true",
            "ContentBasedDeduplication": "true",
            "RedrivePolicy": json.dumps(
                {"deadLetterTargetArn": dead_letter_queue_arn, "maxReceiveCount": 1}
            ),
            "VisibilityTimeout": "1",
        },
    )

    msg_queue.send_message(MessageBody="first", MessageGroupId="1")
    messages = msg_queue.receive_messages()
    assert len(messages) == 1

    time.sleep(1.1)

    messages = msg_queue.receive_messages()
    assert len(messages) == 0

    messages = dlq.receive_messages()
    assert len(messages) == 1

    msg_queue.send_message(MessageBody="second", MessageGroupId="1")
    messages = msg_queue.receive_messages()
    assert len(messages) == 1


@mock_aws
def test_receive_message_using_name_should_return_name_as_url():
    sqs = boto3.resource("sqs", region_name=REGION)
    conn = boto3.client("sqs", region_name=REGION)
    name = str(uuid4())[0:6]
    q_response = conn.create_queue(QueueName=name)
    working_url = q_response["QueueUrl"]
    # https://queue.amazonaws.com/012341234/test-queue
    # http://localhost:5000/012341234/test-queue in ServerMode
    assert working_url.endswith(f"/{ACCOUNT_ID}/{name}")

    queue = sqs.Queue(name)
    queue.send_message(MessageBody="this is a test message")

    resp = queue.receive_messages()
    assert resp[0].queue_url == name


@mock_aws
def test_message_attributes_contains_trace_header():
    sqs = boto3.resource("sqs", region_name=REGION)
    conn = boto3.client("sqs", region_name=REGION)
    q_name = str(uuid4())[0:6]
    q_resp = conn.create_queue(QueueName=q_name)
    queue = sqs.Queue(q_resp["QueueUrl"])
    body_one = "this is a test message"

    queue.send_message(
        MessageBody=body_one,
        MessageSystemAttributes={
            "AWSTraceHeader": {
                "StringValue": (
                    "Root=1-3152b799-8954dae64eda91bc9a23a7e8;"
                    "Parent=7fa8c0f79203be72;Sampled=1"
                ),
                "DataType": "String",
            }
        },
    )

    messages = conn.receive_message(
        QueueUrl=queue.url, MaxNumberOfMessages=2, MessageAttributeNames=["All"]
    )["Messages"]

    assert (
        messages[0]["Attributes"]["AWSTraceHeader"]
        == "Root=1-3152b799-8954dae64eda91bc9a23a7e8;Parent=7fa8c0f79203be72;Sampled=1"
    )


@mock_aws
def test_receive_message_again_preserves_attributes():
    sqs = boto3.resource("sqs", region_name=REGION)
    conn = boto3.client("sqs", region_name=REGION)
    q_name = str(uuid4())[0:6]
    q_resp = conn.create_queue(QueueName=q_name)
    queue = sqs.Queue(q_resp["QueueUrl"])
    body_one = "this is a test message"

    queue.send_message(
        MessageBody=body_one,
        MessageAttributes={
            "Custom1": {"StringValue": "Custom_Value_1", "DataType": "String"},
            "Custom2": {"StringValue": "Custom_Value_2", "DataType": "String"},
        },
    )

    first_messages = conn.receive_message(
        QueueUrl=queue.url,
        MaxNumberOfMessages=2,
        MessageAttributeNames=["Custom1"],
        VisibilityTimeout=0,
    )["Messages"]
    assert len(first_messages[0]["MessageAttributes"]) == 1
    assert first_messages[0]["MessageAttributes"].get("Custom1") is not None
    assert first_messages[0]["MessageAttributes"].get("Custom2") is None

    second_messages = conn.receive_message(
        QueueUrl=queue.url, MaxNumberOfMessages=2, MessageAttributeNames=["All"]
    )["Messages"]
    assert len(second_messages[0]["MessageAttributes"]) == 2
    assert second_messages[0]["MessageAttributes"].get("Custom1") is not None
    assert second_messages[0]["MessageAttributes"].get("Custom2") is not None


@mock_aws
def test_message_has_windows_return():
    sqs = boto3.resource("sqs", region_name=REGION)
    queue = sqs.create_queue(QueueName=f"{str(uuid4())[0:6]}")

    message = "content:\rmessage_with line"
    queue.send_message(MessageBody=message)

    messages = queue.receive_messages()
    assert len(messages) == 1
    assert re.match(message, messages[0].body)


@mock_aws
def test_message_delay_is_more_than_15_minutes():
    client = boto3.client("sqs", region_name=REGION)
    response = client.create_queue(QueueName=str(uuid4())[0:6])
    queue_url = response["QueueUrl"]

    response = client.send_message_batch(
        QueueUrl=queue_url,
        Entries=[
            {
                "Id": "id_1",
                "MessageBody": "body_1",
                "DelaySeconds": 3,
                "MessageAttributes": {
                    "attribute_name_1": {
                        "StringValue": "attribute_value_1",
                        "DataType": "String",
                    }
                },
                "MessageDeduplicationId": "message_deduplication_id_1",
            },
            {
                "Id": "id_2",
                "MessageBody": "body_2",
                "DelaySeconds": 1800,
                "MessageAttributes": {
                    "attribute_name_2": {"StringValue": "123", "DataType": "Number"}
                },
                "MessageDeduplicationId": "message_deduplication_id_2",
            },
        ],
    )

    assert sorted([entry["Id"] for entry in response["Successful"]]) == ["id_1"]

    assert sorted([entry["Id"] for entry in response["Failed"]]) == ["id_2"]

    time.sleep(4)

    response = client.receive_message(
        QueueUrl=queue_url,
        MaxNumberOfMessages=10,
        MessageAttributeNames=["attribute_name_1", "attribute_name_2"],
        AttributeNames=["MessageDeduplicationId", "MessageGroupId"],
    )

    assert len(response["Messages"]) == 1
    assert response["Messages"][0]["Body"] == "body_1"
    assert response["Messages"][0]["MessageAttributes"] == (
        {"attribute_name_1": {"StringValue": "attribute_value_1", "DataType": "String"}}
    )
    assert response["Messages"][0]["Attributes"]["MessageDeduplicationId"] == (
        "message_deduplication_id_1"
    )


@mock_aws
def test_receive_message_that_becomes_visible_while_long_polling():
    sqs = boto3.resource("sqs", region_name=REGION)
    queue = sqs.create_queue(QueueName=str(uuid4())[0:6])
    msg_body = str(uuid4())
    queue.send_message(MessageBody=msg_body)
    messages = queue.receive_messages()
    messages[0].change_visibility(VisibilityTimeout=1)
    time_to_wait = 2
    begin = time.time()
    messages = queue.receive_messages(WaitTimeSeconds=time_to_wait)
    end = time.time()
    assert len(messages) == 1
    assert messages[0].body == msg_body
    assert end - begin < time_to_wait


@mock_aws
def test_dedupe_fifo():
    sqs = boto3.resource("sqs", region_name=REGION)
    queue = sqs.create_queue(
        QueueName="my-queue.fifo",
        Attributes={
            "FifoQueue": "true",
        },
    )

    for _ in range(5):
        queue.send_message(
            MessageBody="test",
            MessageDeduplicationId="1",
            MessageGroupId="2",
        )
    assert int(queue.attributes["ApproximateNumberOfMessages"]) == 1


@mock_aws
def test_fifo_dedupe_error_no_message_group_id():
    sqs = boto3.resource("sqs", region_name=REGION)
    queue = sqs.create_queue(
        QueueName="my-queue.fifo",
        Attributes={"FifoQueue": "true"},
    )
    with pytest.raises(ClientError) as exc:
        queue.send_message(
            MessageBody="test",
            MessageDeduplicationId="1",
        )

    assert exc.value.response["Error"]["Code"] == "MissingParameter"
    assert exc.value.response["Error"]["Message"] == (
        "The request must contain the parameter MessageGroupId."
    )


@mock_aws
def test_fifo_dedupe_error_no_message_dedupe_id():
    sqs = boto3.resource("sqs", region_name=REGION)
    queue = sqs.create_queue(
        QueueName="my-queue.fifo",
        Attributes={"FifoQueue": "true"},
    )
    with pytest.raises(ClientError) as exc:
        queue.send_message(
            MessageBody="test",
            MessageGroupId="1",
        )

    assert exc.value.response["Error"]["Code"] == "InvalidParameterValue"
    assert exc.value.response["Error"]["Message"] == (
        "The queue should either have ContentBasedDeduplication enabled "
        "or MessageDeduplicationId provided explicitly"
    )


@mock_aws
def test_fifo_dedupe_error_no_message_dedupe_id_batch():
    client = boto3.client("sqs", region_name=REGION)
    response = client.create_queue(
        QueueName=f"{str(uuid4())[0:6]}.fifo", Attributes={"FifoQueue": "true"}
    )
    queue_url = response["QueueUrl"]
    with pytest.raises(ClientError) as exc:
        client.send_message_batch(
            QueueUrl=queue_url,
            Entries=[
                {
                    "Id": "id_1",
                    "MessageBody": "body_1",
                    "DelaySeconds": 0,
                    "MessageGroupId": "message_group_id_1",
                    "MessageDeduplicationId": "message_deduplication_id_1",
                },
                {
                    "Id": "id_2",
                    "MessageBody": "body_2",
                    "DelaySeconds": 0,
                    "MessageGroupId": "message_group_id_2",
                },
            ],
        )

    assert exc.value.response["Error"]["Code"] == "InvalidParameterValue"
    assert exc.value.response["Error"]["Message"] == (
        "The queue should either have ContentBasedDeduplication enabled "
        "or MessageDeduplicationId provided explicitly"
    )


@sqs_aws_verified
@pytest.mark.aws_verified
@pytest.mark.parametrize(
    "queue_config", [{"FifoQueue": "true"}, {"FifoQueue": "true", "DelaySeconds": "10"}]
)
def test_send_message_delay_seconds_validation(queue_config):
    # Setup
    client = boto3.client("sqs", region_name=REGION)
    q = f"moto_{str(uuid4())[0:6]}.fifo"
    client.create_queue(QueueName=q, Attributes=queue_config)

    # Execute
    with pytest.raises(ClientError) as err:
        client.send_message(
            QueueUrl=q,
            MessageBody="test",
            DelaySeconds=5,
            MessageGroupId="test",
            MessageDeduplicationId=str(uuid4()),
        )

    # Verify
    ex = err.value
    assert ex.response["Error"]["Code"] == "InvalidParameterValue"
    assert ex.response["Error"]["Message"] == (
        "Value 5 for parameter DelaySeconds is invalid. Reason: "
        "The request include parameter that is not valid for this queue type."
    )

    # this should succeed regardless of DelaySeconds configuration on the q
    # https://docs.aws.amazon.com/AWSSimpleQueueService/latest/APIReference/API_SendMessage.html#API_SendMessage_RequestSyntax
    client.send_message(
        QueueUrl=q,
        MessageBody="test",
        DelaySeconds=0,
        MessageGroupId="test",
        MessageDeduplicationId=str(uuid4()),
    )

    client.send_message(
        QueueUrl=q,
        MessageBody="test",
        MessageGroupId="test",
        MessageDeduplicationId=str(uuid4()),
    )

    # clean up for servertests
    client.delete_queue(QueueUrl=q)
