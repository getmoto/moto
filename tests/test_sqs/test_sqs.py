import base64
import json
import time
import uuid
import hashlib

import boto
import boto3
import botocore.exceptions
import sure  # noqa # pylint: disable=unused-import
from boto.exception import SQSError
from boto.sqs.message import Message, RawMessage
from botocore.exceptions import ClientError
from freezegun import freeze_time
from moto import mock_sqs, mock_sqs_deprecated, settings

from unittest import SkipTest, mock

import pytest
from tests.helpers import requires_boto_gte
from moto.core import ACCOUNT_ID
from moto.sqs.models import (
    Queue,
    MAXIMUM_MESSAGE_SIZE_ATTR_LOWER_BOUND,
    MAXIMUM_MESSAGE_SIZE_ATTR_UPPER_BOUND,
    MAXIMUM_MESSAGE_LENGTH,
)
from uuid import uuid4

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


@mock_sqs
def test_create_fifo_queue_fail():
    sqs = boto3.client("sqs", region_name="us-east-1")

    try:
        sqs.create_queue(QueueName=str(uuid4())[0:6], Attributes={"FifoQueue": "true"})
    except botocore.exceptions.ClientError as err:
        err.response["Error"]["Code"].should.equal("InvalidParameterValue")
    else:
        raise RuntimeError("Should of raised InvalidParameterValue Exception")


@mock_sqs
def test_create_queue_with_same_attributes():
    sqs = boto3.client("sqs", region_name="us-east-1")

    dlq_url = sqs.create_queue(QueueName=str(uuid4()))["QueueUrl"]
    dlq_arn = sqs.get_queue_attributes(QueueUrl=dlq_url, AttributeNames=["All"])[
        "Attributes"
    ]["QueueArn"]

    attributes = {
        "DelaySeconds": "900",
        "MaximumMessageSize": "262144",
        "MessageRetentionPeriod": "1209600",
        "ReceiveMessageWaitTimeSeconds": "20",
        "RedrivePolicy": '{"deadLetterTargetArn": "%s", "maxReceiveCount": 100}'
        % (dlq_arn),
        "VisibilityTimeout": "43200",
    }

    q_name = str(uuid4())[0:6]
    sqs.create_queue(QueueName=q_name, Attributes=attributes)

    sqs.create_queue(QueueName=q_name, Attributes=attributes)


@mock_sqs
def test_create_queue_with_different_attributes_fail():
    sqs = boto3.client("sqs", region_name="us-east-1")

    q_name = str(uuid4())[0:6]
    sqs.create_queue(QueueName=q_name, Attributes={"VisibilityTimeout": "10"})
    try:
        sqs.create_queue(QueueName=q_name, Attributes={"VisibilityTimeout": "60"})
    except botocore.exceptions.ClientError as err:
        err.response["Error"]["Code"].should.equal("QueueAlreadyExists")
    else:
        raise RuntimeError("Should of raised QueueAlreadyExists Exception")

    q_name2 = str(uuid4())[0:6]
    response = sqs.create_queue(QueueName=q_name2, Attributes={"FifoQueue": "True"})

    attributes = {"VisibilityTimeout": "60"}
    sqs.set_queue_attributes(QueueUrl=response.get("QueueUrl"), Attributes=attributes)

    new_response = sqs.create_queue(QueueName=q_name2, Attributes={"FifoQueue": "True"})
    new_response["QueueUrl"].should.equal(response.get("QueueUrl"))


@mock_sqs
def test_create_fifo_queue():
    # given
    region_name = "us-east-1"
    sqs = boto3.client("sqs", region_name=region_name)
    queue_name = f"{str(uuid4())[0:6]}.fifo"

    # when
    queue_url = sqs.create_queue(
        QueueName=queue_name, Attributes={"FifoQueue": "true"}
    )["QueueUrl"]

    # then
    queue_url.should.contain(queue_name)

    attributes = sqs.get_queue_attributes(QueueUrl=queue_url, AttributeNames=["All"])[
        "Attributes"
    ]
    attributes["ApproximateNumberOfMessages"].should.equal("0")
    attributes["ApproximateNumberOfMessagesNotVisible"].should.equal("0")
    attributes["ApproximateNumberOfMessagesDelayed"].should.equal("0")
    attributes["CreatedTimestamp"].should.be.a(str)
    attributes["ContentBasedDeduplication"].should.equal("false")
    attributes["DeduplicationScope"].should.equal("queue")
    attributes["DelaySeconds"].should.equal("0")
    attributes["LastModifiedTimestamp"].should.be.a(str)
    attributes["FifoQueue"].should.equal("true")
    attributes["FifoThroughputLimit"].should.equal("perQueue")
    attributes["MaximumMessageSize"].should.equal("262144")
    attributes["MessageRetentionPeriod"].should.equal("345600")
    attributes["QueueArn"].should.equal(
        f"arn:aws:sqs:{region_name}:{ACCOUNT_ID}:{queue_name}"
    )
    attributes["ReceiveMessageWaitTimeSeconds"].should.equal("0")
    attributes["VisibilityTimeout"].should.equal("30")


@mock_sqs
def test_create_fifo_queue_with_high_throughput():
    # given
    sqs = boto3.client("sqs", region_name="us-east-1")
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
    queue_url.should.contain(queue_name)

    attributes = sqs.get_queue_attributes(QueueUrl=queue_url, AttributeNames=["All"])[
        "Attributes"
    ]
    attributes["DeduplicationScope"].should.equal("messageGroup")
    attributes["FifoQueue"].should.equal("true")
    attributes["FifoThroughputLimit"].should.equal("perMessageGroupId")


@mock_sqs
def test_create_queue():
    sqs = boto3.resource("sqs", region_name="us-east-1")

    q_name = str(uuid4())[0:6]
    new_queue = sqs.create_queue(QueueName=q_name)
    new_queue.should_not.be.none
    new_queue.should.have.property("url").should.contain(q_name)

    queue = sqs.get_queue_by_name(QueueName=q_name)
    queue.attributes.get("QueueArn").should_not.be.none
    queue.attributes.get("QueueArn").split(":")[-1].should.equal(q_name)
    queue.attributes.get("QueueArn").split(":")[3].should.equal("us-east-1")
    queue.attributes.get("VisibilityTimeout").should_not.be.none
    queue.attributes.get("VisibilityTimeout").should.equal("30")


@mock_sqs
def test_create_queue_kms():
    sqs = boto3.resource("sqs", region_name="us-east-1")

    q_name = str(uuid4())[0:6]
    new_queue = sqs.create_queue(
        QueueName=q_name,
        Attributes={
            "KmsMasterKeyId": "master-key-id",
            "KmsDataKeyReusePeriodSeconds": "600",
        },
    )
    new_queue.should_not.be.none

    queue = sqs.get_queue_by_name(QueueName=q_name)

    queue.attributes.get("KmsMasterKeyId").should.equal("master-key-id")
    queue.attributes.get("KmsDataKeyReusePeriodSeconds").should.equal("600")


@mock_sqs
def test_create_queue_with_tags():
    client = boto3.client("sqs", region_name="us-east-1")
    q_name = str(uuid4())[0:6]
    response = client.create_queue(
        QueueName=q_name, tags={"tag_key_1": "tag_value_1", "tag_key_2": ""},
    )
    queue_url = response["QueueUrl"]

    client.list_queue_tags(QueueUrl=queue_url)["Tags"].should.equal(
        {"tag_key_1": "tag_value_1", "tag_key_2": "",}
    )


@mock_sqs
def test_create_queue_with_policy():
    client = boto3.client("sqs", region_name="us-east-1")
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
    json.loads(response["Attributes"]["Policy"]).should.equal(
        {
            "Version": "2012-10-17",
            "Id": "test",
            "Statement": [{"Effect": "Allow", "Principal": "*", "Action": "*"}],
        }
    )


@mock_sqs
def test_set_queue_attribute_empty_policy_removes_attr():
    client = boto3.client("sqs", region_name="us-east-1")
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
    response.shouldnt.have.key("Policy")


def test_is_empty_redrive_policy_returns_true_for_empty_and_falsy_values():
    assert Queue._is_empty_redrive_policy("")
    assert Queue._is_empty_redrive_policy("{}")


def test_is_empty_redrive_policy_returns_false_for_valid_policy_format():
    test_dlq_arn = "arn:aws:sqs:us-east-1:123456789012:test-dlr-queue"
    assert not Queue._is_empty_redrive_policy(
        json.dumps({"deadLetterTargetArn": test_dlq_arn, "maxReceiveCount": 5})
    )
    assert not Queue._is_empty_redrive_policy(json.dumps({"maxReceiveCount": 5}))


@mock_sqs
def test_set_queue_attribute_empty_redrive_removes_attr():
    client = boto3.client("sqs", region_name="us-east-1")

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
    response.shouldnt.have.key("RedrivePolicy")


@mock_sqs
def test_get_queue_url():
    client = boto3.client("sqs", region_name="us-east-1")
    q_name = str(uuid4())[0:6]
    client.create_queue(QueueName=q_name)

    response = client.get_queue_url(QueueName=q_name)

    response.should.have.key("QueueUrl").which.should.contain(q_name)


@mock_sqs
def test_get_queue_url_error_not_exists():
    # given
    client = boto3.client("sqs", region_name="us-east-1")

    # when
    with pytest.raises(ClientError) as e:
        client.get_queue_url(QueueName="not-exists")

    # then
    ex = e.value
    ex.operation_name.should.equal("GetQueueUrl")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain(
        "AWS.SimpleQueueService.NonExistentQueue"
    )
    ex.response["Error"]["Message"].should.equal(
        "The specified queue does not exist for this wsdl version."
    )


@mock_sqs
def test_get_nonexistent_queue():
    sqs = boto3.resource("sqs", region_name="us-east-1")

    with pytest.raises(ClientError) as err:
        sqs.Queue("http://whatever-incorrect-queue-address").load()
    ex = err.value
    ex.operation_name.should.equal("GetQueueAttributes")
    ex.response["Error"]["Code"].should.equal("AWS.SimpleQueueService.NonExistentQueue")
    ex.response["Error"]["Message"].should.equal(
        "The specified queue does not exist for this wsdl version."
    )


@mock_sqs
def test_message_send_without_attributes():
    sqs = boto3.resource("sqs", region_name="us-east-1")
    queue = sqs.create_queue(QueueName=str(uuid4())[0:6])
    msg = queue.send_message(MessageBody="derp")
    msg.get("MD5OfMessageBody").should.equal("58fd9edd83341c29f1aebba81c31e257")
    msg.shouldnt.have.key("MD5OfMessageAttributes")
    msg.get("MessageId").should_not.contain(" \n")

    messages = queue.receive_messages()
    messages.should.have.length_of(1)


@mock_sqs
def test_message_send_with_attributes():
    sqs = boto3.resource("sqs", region_name="us-east-1")
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
    msg.get("MD5OfMessageBody").should.equal("58fd9edd83341c29f1aebba81c31e257")
    msg.get("MD5OfMessageAttributes").should.equal("36655e7e9d7c0e8479fa3f3f42247ae7")
    msg.get("MessageId").should_not.contain(" \n")

    messages = queue.receive_messages()
    messages.should.have.length_of(1)


@mock_sqs
def test_message_retention_period():
    sqs = boto3.resource("sqs", region_name="us-east-1")
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


@mock_sqs
def test_queue_retention_period():
    sqs = boto3.resource("sqs", region_name="us-east-1")
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


@mock_sqs
def test_message_with_invalid_attributes():
    sqs = boto3.resource("sqs", region_name="us-east-1")
    queue = sqs.create_queue(QueueName=str(uuid4())[0:6])
    with pytest.raises(ClientError) as e:
        queue.send_message(
            MessageBody="derp",
            MessageAttributes={
                "öther_encodings": {"DataType": "String", "StringValue": "str"},
            },
        )
    ex = e.value
    ex.response["Error"]["Code"].should.equal("MessageAttributesInvalid")
    ex.response["Error"]["Message"].should.equal(
        "The message attribute name 'öther_encodings' is invalid. "
        "Attribute name can contain A-Z, a-z, 0-9, underscore (_), hyphen (-), and period (.) characters."
    )


@mock_sqs
def test_message_with_string_attributes():
    sqs = boto3.resource("sqs", region_name="us-east-1")
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
    msg.get("MD5OfMessageBody").should.equal("58fd9edd83341c29f1aebba81c31e257")
    msg.get("MD5OfMessageAttributes").should.equal("b12289320bb6e494b18b645ef562b4a9")
    msg.get("MessageId").should_not.contain(" \n")

    messages = queue.receive_messages()
    messages.should.have.length_of(1)


@mock_sqs
def test_message_with_binary_attribute():
    sqs = boto3.resource("sqs", region_name="us-east-1")
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
    msg.get("MD5OfMessageBody").should.equal("58fd9edd83341c29f1aebba81c31e257")
    msg.get("MD5OfMessageAttributes").should.equal("049075255ebc53fb95f7f9f3cedf3c50")
    msg.get("MessageId").should_not.contain(" \n")

    messages = queue.receive_messages()
    messages.should.have.length_of(1)


@mock_sqs
def test_message_with_attributes_have_labels():
    sqs = boto3.resource("sqs", region_name="us-east-1")
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
    msg.get("MD5OfMessageBody").should.equal("58fd9edd83341c29f1aebba81c31e257")
    msg.get("MD5OfMessageAttributes").should.equal("2e2e4876d8e0bd6b8c2c8f556831c349")
    msg.get("MessageId").should_not.contain(" \n")

    messages = queue.receive_messages()
    messages.should.have.length_of(1)


@mock_sqs
def test_message_with_attributes_invalid_datatype():
    sqs = boto3.resource("sqs", region_name="us-east-1")
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
    ex.response["Error"]["Code"].should.equal("MessageAttributesInvalid")
    ex.response["Error"]["Message"].should.equal(
        "The message attribute 'timestamp' has an invalid message attribute type, the set of supported type "
        "prefixes is Binary, Number, and String."
    )


@mock_sqs
def test_send_message_with_message_group_id():
    sqs = boto3.resource("sqs", region_name="us-east-1")
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
    messages.should.have.length_of(1)

    message_attributes = messages[0].attributes
    message_attributes.should.contain("MessageGroupId")
    message_attributes["MessageGroupId"].should.equal("group_id_1")
    message_attributes.should.contain("MessageDeduplicationId")
    message_attributes["MessageDeduplicationId"].should.equal("dedupe_id_1")


@mock_sqs
def test_send_message_with_message_group_id_standard_queue():
    sqs = boto3.resource("sqs", region_name="us-east-1")
    queue = sqs.create_queue(QueueName=str(uuid4())[0:6])

    with pytest.raises(ClientError) as ex:
        queue.send_message(
            MessageBody="mydata", MessageGroupId="group_id_1",
        )

    err = ex.value.response["Error"]
    err["Code"].should.equal("InvalidParameterValue")
    err["Message"].should.equal(
        "Value group_id_1 for parameter MessageGroupId is invalid. "
        "Reason: The request include parameter that is not valid for this queue type."
    )


@mock_sqs
def test_send_message_with_unicode_characters():
    body_one = "Héllo!😀"

    sqs = boto3.resource("sqs", region_name="us-east-1")
    queue = sqs.create_queue(QueueName=str(uuid4())[0:6])
    queue.send_message(MessageBody=body_one)

    messages = queue.receive_messages()
    message_body = messages[0].body

    message_body.should.equal(body_one)


@mock_sqs
def test_set_queue_attributes():
    sqs = boto3.resource("sqs", region_name="us-east-1")
    queue = sqs.create_queue(QueueName=str(uuid4())[0:6])

    queue.attributes["VisibilityTimeout"].should.equal("30")

    queue.set_attributes(Attributes={"VisibilityTimeout": "45"})
    queue.attributes["VisibilityTimeout"].should.equal("45")


@mock_sqs
def test_create_queues_in_multiple_region():
    w1 = boto3.client("sqs", region_name="us-west-1")
    w1_name = str(uuid4())[0:6]
    w1.create_queue(QueueName=w1_name)

    w2 = boto3.client("sqs", region_name="us-west-2")
    w2_name = str(uuid4())[0:6]
    w2.create_queue(QueueName=w2_name)

    base_url = (
        "http://localhost:5000"
        if settings.TEST_SERVER_MODE
        else "https://us-west-1.queue.amazonaws.com"
    )
    w1.list_queues()["QueueUrls"].should.contain(f"{base_url}/{ACCOUNT_ID}/{w1_name}")
    w1.list_queues()["QueueUrls"].shouldnt.contain(f"{base_url}/{ACCOUNT_ID}/{w2_name}")

    base_url = (
        "http://localhost:5000"
        if settings.TEST_SERVER_MODE
        else "https://us-west-2.queue.amazonaws.com"
    )
    w2.list_queues()["QueueUrls"].shouldnt.contain(f"{base_url}/{ACCOUNT_ID}/{w1_name}")
    w2.list_queues()["QueueUrls"].should.contain(f"{base_url}/{ACCOUNT_ID}/{w2_name}")


@mock_sqs
def test_get_queue_with_prefix():
    conn = boto3.client("sqs", region_name="us-west-1")
    conn.create_queue(QueueName=str(uuid4())[0:6])
    q_name1 = str(uuid4())[0:6]
    conn.create_queue(QueueName=q_name1)
    prefix = str(uuid4())[0:6]
    q_name2 = f"{prefix}-test"
    conn.create_queue(QueueName=q_name2)

    base_url = (
        "http://localhost:5000"
        if settings.TEST_SERVER_MODE
        else "https://us-west-1.queue.amazonaws.com"
    )
    expected_url1 = f"{base_url}/{ACCOUNT_ID}/{q_name1}"
    expected_url2 = f"{base_url}/{ACCOUNT_ID}/{q_name2}"

    all_urls = conn.list_queues()["QueueUrls"]
    all_urls.should.contain(expected_url1)
    all_urls.should.contain(expected_url2)

    queue = conn.list_queues(QueueNamePrefix=prefix)["QueueUrls"]
    queue.should.have.length_of(1)

    queue[0].should.equal(expected_url2)


@mock_sqs
def test_delete_queue():
    sqs = boto3.resource("sqs", region_name="us-east-1")
    conn = boto3.client("sqs", region_name="us-east-1")
    q_name = str(uuid4())[0:6]
    q_resp = conn.create_queue(QueueName=q_name, Attributes={"VisibilityTimeout": "3"})
    queue = sqs.Queue(q_resp["QueueUrl"])

    all_urls = conn.list_queues()["QueueUrls"]
    [u[u.rfind("/") + 1 :] for u in all_urls].should.contain(q_name)

    queue.delete()

    all_urls = conn.list_queues().get("QueueUrls", [])
    [u[u.rfind("/") + 1 :] for u in all_urls].shouldnt.contain(q_name)


@mock_sqs
def test_delete_queue_error_not_exists():
    client = boto3.client("sqs", region_name="us-east-1")

    with pytest.raises(ClientError) as e:
        client.delete_queue(
            QueueUrl=f"https://queue.amazonaws.com/{ACCOUNT_ID}/not-exists"
        )

    ex = e.value
    ex.operation_name.should.equal("DeleteQueue")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain(
        "AWS.SimpleQueueService.NonExistentQueue"
    )
    ex.response["Error"]["Message"].should.equal(
        "The specified queue does not exist for this wsdl version."
    )


@mock_sqs
def test_get_queue_attributes():
    client = boto3.client("sqs", region_name="us-east-1")

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

    response["Attributes"]["ApproximateNumberOfMessages"].should.equal("0")
    response["Attributes"]["ApproximateNumberOfMessagesDelayed"].should.equal("0")
    response["Attributes"]["ApproximateNumberOfMessagesNotVisible"].should.equal("0")
    response["Attributes"]["CreatedTimestamp"].should.be.a(str)
    response["Attributes"]["DelaySeconds"].should.equal("0")
    response["Attributes"]["LastModifiedTimestamp"].should.be.a(str)
    response["Attributes"]["MaximumMessageSize"].should.equal("262144")
    response["Attributes"]["MessageRetentionPeriod"].should.equal("345600")
    response["Attributes"]["QueueArn"].should.equal(
        "arn:aws:sqs:us-east-1:{}:{}".format(ACCOUNT_ID, q_name)
    )
    response["Attributes"]["ReceiveMessageWaitTimeSeconds"].should.equal("0")
    response["Attributes"]["VisibilityTimeout"].should.equal("30")

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

    response["Attributes"].should.equal(
        {
            "ApproximateNumberOfMessages": "0",
            "MaximumMessageSize": "262144",
            "QueueArn": "arn:aws:sqs:us-east-1:{}:{}".format(ACCOUNT_ID, q_name),
            "VisibilityTimeout": "30",
            "RedrivePolicy": json.dumps(
                {"deadLetterTargetArn": dlq_arn1, "maxReceiveCount": 2}
            ),
        }
    )

    # should not return any attributes, if it was not set before
    response = client.get_queue_attributes(
        QueueUrl=queue_url, AttributeNames=["KmsMasterKeyId"]
    )

    response.should_not.have.key("Attributes")


@mock_sqs
def test_get_queue_attributes_errors():
    client = boto3.client("sqs", region_name="us-east-1")
    response = client.create_queue(QueueName=str(uuid4())[0:6])
    queue_url = response["QueueUrl"]

    client.get_queue_attributes.when.called_with(
        QueueUrl=queue_url,
        AttributeNames=["QueueArn", "not-existing", "VisibilityTimeout"],
    ).should.throw(ClientError, "Unknown Attribute not-existing.")

    client.get_queue_attributes.when.called_with(
        QueueUrl=queue_url, AttributeNames=[""]
    ).should.throw(ClientError, "Unknown Attribute .")

    client.get_queue_attributes.when.called_with(
        QueueUrl=queue_url, AttributeNames=[]
    ).should.throw(ClientError, "Unknown Attribute .")


@mock_sqs
def test_get_queue_attributes_error_not_exists():
    # given
    client = boto3.client("sqs", region_name="us-east-1")

    # when
    with pytest.raises(ClientError) as e:
        client.get_queue_attributes(
            QueueUrl=f"https://queue.amazonaws.com/{ACCOUNT_ID}/not-exists"
        )

    # then
    ex = e.value
    ex.operation_name.should.equal("GetQueueAttributes")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain(
        "AWS.SimpleQueueService.NonExistentQueue"
    )
    ex.response["Error"]["Message"].should.equal(
        "The specified queue does not exist for this wsdl version."
    )


@mock_sqs
def test_set_queue_attribute():
    sqs = boto3.resource("sqs", region_name="us-east-1")
    conn = boto3.client("sqs", region_name="us-east-1")
    q_resp = conn.create_queue(
        QueueName=str(uuid4())[0:6], Attributes={"VisibilityTimeout": "3"}
    )

    queue = sqs.Queue(q_resp["QueueUrl"])
    queue.attributes["VisibilityTimeout"].should.equal("3")

    queue.set_attributes(Attributes={"VisibilityTimeout": "45"})
    queue = sqs.Queue(q_resp["QueueUrl"])
    queue.attributes["VisibilityTimeout"].should.equal("45")


@mock_sqs
def test_send_receive_message_without_attributes():
    sqs = boto3.resource("sqs", region_name="us-east-1")
    conn = boto3.client("sqs", region_name="us-east-1")
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

    message1["Body"].should.equal(body_one)
    message2["Body"].should.equal(body_two)

    message1.shouldnt.have.key("MD5OfMessageAttributes")
    message2.shouldnt.have.key("MD5OfMessageAttributes")

    message1.should_not.have.key("Attributes")
    message2.should_not.have.key("Attributes")


@mock_sqs
def test_send_receive_message_with_attributes():
    sqs = boto3.resource("sqs", region_name="us-east-1")
    conn = boto3.client("sqs", region_name="us-east-1")
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

    message1.get("Body").should.equal(body_one)
    message2.get("Body").should.equal(body_two)

    message1.get("MD5OfMessageAttributes").should.equal(
        "235c5c510d26fb653d073faed50ae77c"
    )
    message2.get("MD5OfMessageAttributes").should.equal(
        "994258b45346a2cc3f9cbb611aa7af30"
    )


@mock_sqs
def test_send_receive_message_with_attributes_with_labels():
    sqs = boto3.resource("sqs", region_name="us-east-1")
    conn = boto3.client("sqs", region_name="us-east-1")
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

    message1.get("Body").should.equal(body_one)
    message2.get("Body").should.equal(body_two)

    message1.get("MD5OfMessageAttributes").should.equal(
        "2e2e4876d8e0bd6b8c2c8f556831c349"
    )
    message2.get("MD5OfMessageAttributes").should.equal(
        "cfa7c73063c6e2dbf9be34232a1978cf"
    )

    response = queue.send_message(
        MessageBody="test message",
        MessageAttributes={
            "somevalue": {"StringValue": "somevalue", "DataType": "String.custom",}
        },
    )

    response.get("MD5OfMessageAttributes").should.equal(
        "9e05cca738e70ff6c6041e82d5e77ef1"
    )


@mock_sqs
def test_receive_message_with_xml_content():
    sqs = boto3.client("sqs", region_name="eu-west-2")
    queue_url = sqs.create_queue(QueueName=str(uuid4())[0:6])["QueueUrl"]
    original_payload = '<?xml version="1.0" encoding="UTF-8"?><feed xmlns="http://www.w3.org/2005/Atom"/>'
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
    attr.should.equal(original_payload)


@mock_sqs
def test_change_message_visibility_than_permitted():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Cant manipulate time in server mode")

    sqs = boto3.resource("sqs", region_name="us-east-1")
    conn = boto3.client("sqs", region_name="us-east-1")

    with freeze_time("2015-01-01 12:00:00"):
        q_resp = conn.create_queue(QueueName="test-queue-visibility")
        queue = sqs.Queue(q_resp["QueueUrl"])
        queue.send_message(MessageBody="derp")
        messages = conn.receive_message(QueueUrl=queue.url)
        messages.get("Messages").should.have.length_of(1)

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
        ex.operation_name.should.equal("ChangeMessageVisibility")
        ex.response["Error"]["Code"].should.equal("InvalidParameterValue")


@mock_sqs
def test_send_receive_message_timestamps():
    sqs = boto3.resource("sqs", region_name="us-east-1")
    conn = boto3.client("sqs", region_name="us-east-1")
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

    int.when.called_with(sent_timestamp).shouldnt.throw(ValueError)
    int.when.called_with(approximate_first_receive_timestamp).shouldnt.throw(ValueError)


@mock_sqs
@pytest.mark.parametrize(
    "attribute_name,expected",
    [
        (
            "All",
            {
                "ApproximateFirstReceiveTimestamp": lambda x: x.should_not.be.empty,
                "ApproximateReceiveCount": lambda x: x.should.equal("1"),
                "MessageDeduplicationId": lambda x: x.should.be.none,
                "MessageGroupId": lambda x: x.should.be.none,
                "SenderId": lambda x: x.should_not.be.empty,
                "SentTimestamp": lambda x: x.should_not.be.empty,
                "SequenceNumber": lambda x: x.should.be.none,
            },
        ),
        (
            "ApproximateFirstReceiveTimestamp",
            {
                "ApproximateFirstReceiveTimestamp": lambda x: x.should_not.be.empty,
                "ApproximateReceiveCount": lambda x: x.should.be.none,
                "MessageDeduplicationId": lambda x: x.should.be.none,
                "MessageGroupId": lambda x: x.should.be.none,
                "SenderId": lambda x: x.should.be.none,
                "SentTimestamp": lambda x: x.should.be.none,
                "SequenceNumber": lambda x: x.should.be.none,
            },
        ),
        (
            "ApproximateReceiveCount",
            {
                "ApproximateFirstReceiveTimestamp": lambda x: x.should.be.none,
                "ApproximateReceiveCount": lambda x: x.should.equal("1"),
                "MessageDeduplicationId": lambda x: x.should.be.none,
                "MessageGroupId": lambda x: x.should.be.none,
                "SenderId": lambda x: x.should.be.none,
                "SentTimestamp": lambda x: x.should.be.none,
                "SequenceNumber": lambda x: x.should.be.none,
            },
        ),
        (
            "SenderId",
            {
                "ApproximateFirstReceiveTimestamp": lambda x: x.should.be.none,
                "ApproximateReceiveCount": lambda x: x.should.be.none,
                "MessageDeduplicationId": lambda x: x.should.be.none,
                "MessageGroupId": lambda x: x.should.be.none,
                "SenderId": lambda x: x.should_not.be.empty,
                "SentTimestamp": lambda x: x.should.be.none,
                "SequenceNumber": lambda x: x.should.be.none,
            },
        ),
        (
            "SentTimestamp",
            {
                "ApproximateFirstReceiveTimestamp": lambda x: x.should.be.none,
                "ApproximateReceiveCount": lambda x: x.should.be.none,
                "MessageDeduplicationId": lambda x: x.should.be.none,
                "MessageGroupId": lambda x: x.should.be.none,
                "SenderId": lambda x: x.should.be.none,
                "SentTimestamp": lambda x: x.should_not.be.empty,
                "SequenceNumber": lambda x: x.should.be.none,
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
    sqs = boto3.resource("sqs", region_name="us-east-1")
    client = boto3.client("sqs", region_name="us-east-1")
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

    message1["Body"].should.equal(body_one)
    message2["Body"].should.equal(body_two)

    message1.shouldnt.have.key("MD5OfMessageAttributes")
    message2.shouldnt.have.key("MD5OfMessageAttributes")

    expected["ApproximateFirstReceiveTimestamp"](
        message1["Attributes"].get("ApproximateFirstReceiveTimestamp")
    )
    expected["ApproximateReceiveCount"](
        message1["Attributes"].get("ApproximateReceiveCount")
    )
    expected["MessageDeduplicationId"](
        message1["Attributes"].get("MessageDeduplicationId")
    )
    expected["MessageGroupId"](message1["Attributes"].get("MessageGroupId"))
    expected["SenderId"](message1["Attributes"].get("SenderId"))
    expected["SentTimestamp"](message1["Attributes"].get("SentTimestamp"))
    expected["SequenceNumber"](message1["Attributes"].get("SequenceNumber"))

    expected["ApproximateFirstReceiveTimestamp"](
        message2["Attributes"].get("ApproximateFirstReceiveTimestamp")
    )
    expected["ApproximateReceiveCount"](
        message2["Attributes"].get("ApproximateReceiveCount")
    )
    expected["MessageDeduplicationId"](
        message2["Attributes"].get("MessageDeduplicationId")
    )
    expected["MessageGroupId"](message2["Attributes"].get("MessageGroupId"))
    expected["SenderId"](message2["Attributes"].get("SenderId"))
    expected["SentTimestamp"](message2["Attributes"].get("SentTimestamp"))
    expected["SequenceNumber"](message2["Attributes"].get("SequenceNumber"))


@mock_sqs
@pytest.mark.parametrize(
    "attribute_name,expected",
    [
        (
            "All",
            {
                "ApproximateFirstReceiveTimestamp": lambda x: x.should_not.be.empty,
                "ApproximateReceiveCount": lambda x: x.should.equal("1"),
                "MessageDeduplicationId": lambda x: x.should.equal("123"),
                "MessageGroupId": lambda x: x.should.equal("456"),
                "SenderId": lambda x: x.should_not.be.empty,
                "SentTimestamp": lambda x: x.should_not.be.empty,
                "SequenceNumber": lambda x: x.should_not.be.empty,
            },
        ),
        (
            "ApproximateFirstReceiveTimestamp",
            {
                "ApproximateFirstReceiveTimestamp": lambda x: x.should_not.be.empty,
                "ApproximateReceiveCount": lambda x: x.should.be.none,
                "MessageDeduplicationId": lambda x: x.should.be.none,
                "MessageGroupId": lambda x: x.should.be.none,
                "SenderId": lambda x: x.should.be.none,
                "SentTimestamp": lambda x: x.should.be.none,
                "SequenceNumber": lambda x: x.should.be.none,
            },
        ),
        (
            "ApproximateReceiveCount",
            {
                "ApproximateFirstReceiveTimestamp": lambda x: x.should.be.none,
                "ApproximateReceiveCount": lambda x: x.should.equal("1"),
                "MessageDeduplicationId": lambda x: x.should.be.none,
                "MessageGroupId": lambda x: x.should.be.none,
                "SenderId": lambda x: x.should.be.none,
                "SentTimestamp": lambda x: x.should.be.none,
                "SequenceNumber": lambda x: x.should.be.none,
            },
        ),
        (
            "MessageDeduplicationId",
            {
                "ApproximateFirstReceiveTimestamp": lambda x: x.should.be.none,
                "ApproximateReceiveCount": lambda x: x.should.be.none,
                "MessageDeduplicationId": lambda x: x.should.equal("123"),
                "MessageGroupId": lambda x: x.should.be.none,
                "SenderId": lambda x: x.should.be.none,
                "SentTimestamp": lambda x: x.should.be.none,
                "SequenceNumber": lambda x: x.should.be.none,
            },
        ),
        (
            "MessageGroupId",
            {
                "ApproximateFirstReceiveTimestamp": lambda x: x.should.be.none,
                "ApproximateReceiveCount": lambda x: x.should.be.none,
                "MessageDeduplicationId": lambda x: x.should.be.none,
                "MessageGroupId": lambda x: x.should.equal("456"),
                "SenderId": lambda x: x.should.be.none,
                "SentTimestamp": lambda x: x.should.be.none,
                "SequenceNumber": lambda x: x.should.be.none,
            },
        ),
        (
            "SenderId",
            {
                "ApproximateFirstReceiveTimestamp": lambda x: x.should.be.none,
                "ApproximateReceiveCount": lambda x: x.should.be.none,
                "MessageDeduplicationId": lambda x: x.should.be.none,
                "MessageGroupId": lambda x: x.should.be.none,
                "SenderId": lambda x: x.should_not.be.empty,
                "SentTimestamp": lambda x: x.should.be.none,
                "SequenceNumber": lambda x: x.should.be.none,
            },
        ),
        (
            "SentTimestamp",
            {
                "ApproximateFirstReceiveTimestamp": lambda x: x.should.be.none,
                "ApproximateReceiveCount": lambda x: x.should.be.none,
                "MessageDeduplicationId": lambda x: x.should.be.none,
                "MessageGroupId": lambda x: x.should.be.none,
                "SenderId": lambda x: x.should.be.none,
                "SentTimestamp": lambda x: x.should_not.be.empty,
                "SequenceNumber": lambda x: x.should.be.none,
            },
        ),
        (
            "SequenceNumber",
            {
                "ApproximateFirstReceiveTimestamp": lambda x: x.should.be.none,
                "ApproximateReceiveCount": lambda x: x.should.be.none,
                "MessageDeduplicationId": lambda x: x.should.be.none,
                "MessageGroupId": lambda x: x.should.be.none,
                "SenderId": lambda x: x.should.be.none,
                "SentTimestamp": lambda x: x.should.be.none,
                "SequenceNumber": lambda x: x.should_not.be.empty,
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
    client = boto3.client("sqs", region_name="us-east-1")
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

    message["Body"].should.equal(body)

    message.should_not.have.key("MD5OfMessageAttributes")

    expected["ApproximateFirstReceiveTimestamp"](
        message["Attributes"].get("ApproximateFirstReceiveTimestamp")
    )
    expected["ApproximateReceiveCount"](
        message["Attributes"].get("ApproximateReceiveCount")
    )
    expected["MessageDeduplicationId"](
        message["Attributes"].get("MessageDeduplicationId")
    )
    expected["MessageGroupId"](message["Attributes"].get("MessageGroupId"))
    expected["SenderId"](message["Attributes"].get("SenderId"))
    expected["SentTimestamp"](message["Attributes"].get("SentTimestamp"))
    expected["SequenceNumber"](message["Attributes"].get("SequenceNumber"))


@mock_sqs
def test_get_queue_attributes_no_param():
    """
    AWS does not return the Attributes-key when omitting the AttributeNames-parameter
    """
    sqs = boto3.client("sqs", region_name="ap-northeast-3")
    queue_url = sqs.create_queue(QueueName=str(uuid4())[0:6])["QueueUrl"]

    queue_attrs = sqs.get_queue_attributes(QueueUrl=queue_url)
    queue_attrs.shouldnt.have.key("Attributes")

    queue_attrs = sqs.get_queue_attributes(QueueUrl=queue_url, AttributeNames=["All"])
    queue_attrs.should.have.key("Attributes")


@mock_sqs
def test_max_number_of_messages_invalid_param():
    sqs = boto3.resource("sqs", region_name="us-east-1")
    queue = sqs.create_queue(QueueName=str(uuid4())[0:6])

    with pytest.raises(ClientError):
        queue.receive_messages(MaxNumberOfMessages=11)

    with pytest.raises(ClientError):
        queue.receive_messages(MaxNumberOfMessages=0)

    # no error but also no messages returned
    queue.receive_messages(MaxNumberOfMessages=1, WaitTimeSeconds=0)


@mock_sqs
def test_wait_time_seconds_invalid_param():
    sqs = boto3.resource("sqs", region_name="us-east-1")
    queue = sqs.create_queue(QueueName=str(uuid4())[0:6])

    with pytest.raises(ClientError):
        queue.receive_messages(WaitTimeSeconds=-1)

    with pytest.raises(ClientError):
        queue.receive_messages(WaitTimeSeconds=21)

    # no error but also no messages returned
    queue.receive_messages(WaitTimeSeconds=0)


@mock_sqs
def test_receive_messages_with_wait_seconds_timeout_of_zero():
    """
    test that zero messages is returned with a wait_seconds_timeout of zero,
    previously this created an infinite loop and nothing was returned
    :return:
    """

    sqs = boto3.resource("sqs", region_name="us-east-1")
    queue = sqs.create_queue(QueueName=str(uuid4())[0:6])

    messages = queue.receive_messages(WaitTimeSeconds=0)
    messages.should.equal([])


# Has boto3 equivalent
@mock_sqs_deprecated
def test_send_message_with_xml_characters():
    conn = boto.connect_sqs("the_key", "the_secret")
    queue = conn.create_queue("test-queue", visibility_timeout=3)
    queue.set_message_class(RawMessage)

    body_one = "< & >"

    queue.write(queue.new_message(body_one))

    messages = conn.receive_message(queue, number_messages=1)

    messages[0].get_body().should.equal(body_one)


@mock_sqs
def test_send_message_with_xml_characters_boto3():
    sqs = boto3.resource("sqs", region_name="us-east-1")
    client = boto3.client("sqs", region_name="us-east-1")
    queue = sqs.create_queue(QueueName=str(uuid4())[0:6])

    body_one = "< & >"

    queue.send_message(MessageBody=body_one)

    messages = client.receive_message(QueueUrl=queue.url)["Messages"]

    messages[0]["Body"].should.equal(body_one)


# Has boto3 equivalent
@requires_boto_gte("2.28")
@mock_sqs_deprecated
def test_send_message_with_attributes():
    conn = boto.connect_sqs("the_key", "the_secret")
    queue = conn.create_queue("test-queue", visibility_timeout=3)
    queue.set_message_class(RawMessage)

    body = "this is a test message"
    message = queue.new_message(body)
    BASE64_BINARY = base64.b64encode(b"binary value").decode("utf-8")
    message_attributes = {
        "test.attribute_name": {
            "data_type": "String",
            "string_value": "attribute value",
        },
        "test.binary_attribute": {"data_type": "Binary", "binary_value": BASE64_BINARY},
        "test.number_attribute": {
            "data_type": "Number",
            "string_value": "string value",
        },
    }
    message.message_attributes = message_attributes

    queue.write(message)

    messages = conn.receive_message(
        queue,
        message_attributes=[
            "test.attribute_name",
            "test.binary_attribute",
            "test.number_attribute",
        ],
    )

    messages[0].get_body().should.equal(body)

    for name, value in message_attributes.items():
        dict(messages[0].message_attributes[name]).should.equal(value)


# Has boto3 equivalent
@mock_sqs_deprecated
def test_send_message_with_delay():
    conn = boto.connect_sqs("the_key", "the_secret")
    queue = conn.create_queue("test-queue", visibility_timeout=3)
    queue.set_message_class(RawMessage)

    body_one = "this is a test message"
    body_two = "this is another test message"

    queue.write(queue.new_message(body_one), delay_seconds=3)
    queue.write(queue.new_message(body_two))

    queue.count().should.equal(1)

    messages = conn.receive_message(queue, number_messages=2)
    assert len(messages) == 1
    message = messages[0]
    assert message.get_body().should.equal(body_two)
    queue.count().should.equal(0)


@mock_sqs
def test_send_message_with_delay_boto3():
    sqs = boto3.resource("sqs", region_name="us-east-1")
    queue = sqs.create_queue(QueueName=str(uuid4())[0:6])

    body_one = "this is a test message"
    body_two = "this is another test message"

    queue.send_message(MessageBody=body_one, DelaySeconds=3)
    queue.send_message(MessageBody=body_two)

    messages = queue.receive_messages()
    messages.should.have.length_of(1)

    messages[0].body.should.equal(body_two)

    messages = queue.receive_messages()
    messages.should.have.length_of(0)


# Has boto3 equivalent
@mock_sqs_deprecated
def test_send_large_message_fails():
    conn = boto.connect_sqs("the_key", "the_secret")
    queue = conn.create_queue("test-queue", visibility_timeout=3)
    queue.set_message_class(RawMessage)

    body_one = "test message" * 200000
    huge_message = queue.new_message(body_one)

    queue.write.when.called_with(huge_message).should.throw(SQSError)


@mock_sqs
def test_send_large_message_fails_boto3():
    sqs = boto3.resource("sqs", region_name="us-east-1")
    queue = sqs.create_queue(QueueName=str(uuid4())[0:6])

    body = "test message" * 200000
    with pytest.raises(ClientError) as ex:
        queue.send_message(MessageBody=body)
    err = ex.value.response["Error"]
    err["Code"].should.equal("InvalidParameterValue")
    err["Message"].should.equal(
        "One or more parameters are invalid. Reason: Message must be shorter than 262144 bytes."
    )


# Has boto3 equivalent
@mock_sqs_deprecated
def test_message_becomes_inflight_when_received():
    conn = boto.connect_sqs("the_key", "the_secret")
    queue = conn.create_queue("test-queue", visibility_timeout=2)
    queue.set_message_class(RawMessage)

    body_one = "this is a test message"
    queue.write(queue.new_message(body_one))
    queue.count().should.equal(1)

    messages = conn.receive_message(queue, number_messages=1)
    queue.count().should.equal(0)

    assert len(messages) == 1

    # Wait
    time.sleep(3)

    queue.count().should.equal(1)


@mock_sqs
def test_message_becomes_inflight_when_received_boto3():
    sqs = boto3.resource("sqs", region_name="eu-west-1")
    queue = sqs.create_queue(
        QueueName=str(uuid4())[0:6], Attributes={"VisibilityTimeout ": "2"}
    )

    queue.attributes["ApproximateNumberOfMessages"].should.equal("0")

    body = "this is a test message"
    queue.send_message(MessageBody=body)

    queue.reload()
    queue.attributes["ApproximateNumberOfMessages"].should.equal("1")

    messages = queue.receive_messages()
    messages.should.have.length_of(1)

    queue.reload()
    queue.attributes["ApproximateNumberOfMessages"].should.equal("0")

    # Wait
    time.sleep(3)

    queue.reload()
    queue.attributes["ApproximateNumberOfMessages"].should.equal("1")


# Has boto3 equivalent
@mock_sqs_deprecated
def test_receive_message_with_explicit_visibility_timeout():
    conn = boto.connect_sqs("the_key", "the_secret")
    queue = conn.create_queue("test-queue", visibility_timeout=3)
    queue.set_message_class(RawMessage)

    body_one = "this is another test message"
    queue.write(queue.new_message(body_one))

    queue.count().should.equal(1)
    messages = conn.receive_message(queue, number_messages=1, visibility_timeout=0)

    assert len(messages) == 1

    # Message should remain visible
    queue.count().should.equal(1)


@mock_sqs
def test_receive_message_with_explicit_visibility_timeout_boto3():
    sqs = boto3.resource("sqs", region_name="us-east-1")
    queue = sqs.create_queue(
        QueueName=str(uuid4())[0:6], Attributes={"VisibilityTimeout ": "1"}
    )

    queue.attributes["ApproximateNumberOfMessages"].should.equal("0")

    body = "this is a test message"
    queue.send_message(MessageBody=body)

    queue.reload()
    queue.attributes["ApproximateNumberOfMessages"].should.equal("1")

    messages = queue.receive_messages(VisibilityTimeout=0)
    messages.should.have.length_of(1)

    queue.reload()
    queue.attributes["ApproximateNumberOfMessages"].should.equal("1")


# Has boto3 equivalent
@mock_sqs_deprecated
def test_change_message_visibility():
    conn = boto.connect_sqs("the_key", "the_secret")
    queue = conn.create_queue("test-queue", visibility_timeout=2)
    queue.set_message_class(RawMessage)

    body_one = "this is another test message"
    queue.write(queue.new_message(body_one))

    queue.count().should.equal(1)
    messages = conn.receive_message(queue, number_messages=1)

    assert len(messages) == 1

    queue.count().should.equal(0)

    messages[0].change_visibility(2)

    # Wait
    time.sleep(1)

    # Message is not visible
    queue.count().should.equal(0)

    time.sleep(2)

    # Message now becomes visible
    queue.count().should.equal(1)

    messages = conn.receive_message(queue, number_messages=1)
    messages[0].delete()
    queue.count().should.equal(0)


@mock_sqs
def test_change_message_visibility_boto3():
    sqs = boto3.resource("sqs", region_name="us-east-1")
    queue = sqs.create_queue(
        QueueName=str(uuid4())[0:6], Attributes={"VisibilityTimeout ": "2"}
    )

    body = "this is a test message"
    queue.send_message(MessageBody=body)

    queue.reload()
    queue.attributes["ApproximateNumberOfMessages"].should.equal("1")
    messages = queue.receive_messages()

    messages.should.have.length_of(1)

    queue.reload()
    queue.attributes["ApproximateNumberOfMessages"].should.equal("0")

    messages[0].change_visibility(VisibilityTimeout=2)

    # Wait
    time.sleep(1)

    # Message is not visible
    queue.reload()
    queue.attributes["ApproximateNumberOfMessages"].should.equal("0")

    time.sleep(2)

    # Message now becomes visible
    queue.reload()
    queue.attributes["ApproximateNumberOfMessages"].should.equal("1")

    messages = queue.receive_messages()
    messages[0].delete()
    queue.reload()
    queue.attributes["ApproximateNumberOfMessages"].should.equal("0")


@mock_sqs
def test_change_message_visibility_on_unknown_receipt_handle():
    sqs = boto3.resource("sqs", region_name="us-east-1")
    conn = boto3.client("sqs", region_name="us-east-1")
    queue = sqs.create_queue(
        QueueName=str(uuid4())[0:6], Attributes={"VisibilityTimeout": "2"}
    )

    with pytest.raises(ClientError) as exc:
        conn.change_message_visibility(
            QueueUrl=queue.url, ReceiptHandle="unknown-stuff", VisibilityTimeout=432,
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("ReceiptHandleIsInvalid")
    err["Message"].should.equal("The input receipt handle is invalid.")


# Has boto3 equivalent
@mock_sqs_deprecated
def test_message_attributes():
    conn = boto.connect_sqs("the_key", "the_secret")
    queue = conn.create_queue("test-queue", visibility_timeout=2)
    queue.set_message_class(RawMessage)

    body_one = "this is another test message"
    queue.write(queue.new_message(body_one))

    queue.count().should.equal(1)

    messages = conn.receive_message(queue, number_messages=1, attributes=["All"])
    queue.count().should.equal(0)

    assert len(messages) == 1

    message_attributes = messages[0].attributes

    assert message_attributes.get("ApproximateFirstReceiveTimestamp")
    assert int(message_attributes.get("ApproximateReceiveCount")) == 1
    assert message_attributes.get("SentTimestamp")
    assert message_attributes.get("SenderId")


# Has boto3 equivalent
@mock_sqs_deprecated
def test_read_message_from_queue():
    conn = boto.connect_sqs()
    queue = conn.create_queue("testqueue")
    queue.set_message_class(RawMessage)

    body = "foo bar baz"
    queue.write(queue.new_message(body))
    message = queue.read(1)
    message.get_body().should.equal(body)


# Has boto3 equivalent
@mock_sqs_deprecated
def test_queue_length():
    conn = boto.connect_sqs("the_key", "the_secret")
    queue = conn.create_queue("test-queue", visibility_timeout=3)
    queue.set_message_class(RawMessage)

    queue.write(queue.new_message("this is a test message"))
    queue.write(queue.new_message("this is another test message"))
    queue.count().should.equal(2)


@mock_sqs
def test_queue_length_boto3():
    sqs = boto3.resource("sqs", region_name="us-east-1")
    queue = sqs.create_queue(
        QueueName=str(uuid4())[0:6], Attributes={"VisibilityTimeout ": "2"}
    )

    queue.send_message(MessageBody="this is a test message")
    queue.send_message(MessageBody="this is another test message")

    queue.reload()
    queue.attributes["ApproximateNumberOfMessages"].should.equal("2")


# Has boto3 equivalent
@mock_sqs_deprecated
def test_delete_message():
    conn = boto.connect_sqs("the_key", "the_secret")
    queue = conn.create_queue("test-queue", visibility_timeout=3)
    queue.set_message_class(RawMessage)

    queue.write(queue.new_message("this is a test message"))
    queue.write(queue.new_message("this is another test message"))
    queue.count().should.equal(2)

    messages = conn.receive_message(queue, number_messages=1)
    assert len(messages) == 1
    messages[0].delete()
    queue.count().should.equal(1)

    messages = conn.receive_message(queue, number_messages=1)
    assert len(messages) == 1
    messages[0].delete()
    queue.count().should.equal(0)


# Has boto3 equivalent
@mock_sqs_deprecated
def test_send_batch_operation():
    conn = boto.connect_sqs("the_key", "the_secret")
    queue = conn.create_queue("test-queue", visibility_timeout=3)

    # See https://github.com/boto/boto/issues/831
    queue.set_message_class(RawMessage)

    queue.write_batch(
        [
            ("my_first_message", "test message 1", 0),
            ("my_second_message", "test message 2", 0),
            ("my_third_message", "test message 3", 0),
        ]
    )

    messages = queue.get_messages(3)
    messages[0].get_body().should.equal("test message 1")

    # Test that pulling more messages doesn't break anything
    messages = queue.get_messages(2)


# Has boto3 equivalent
@requires_boto_gte("2.28")
@mock_sqs_deprecated
def test_send_batch_operation_with_message_attributes():
    conn = boto.connect_sqs("the_key", "the_secret")
    queue = conn.create_queue("test-queue", visibility_timeout=3)
    queue.set_message_class(RawMessage)

    message_tuple = (
        "my_first_message",
        "test message 1",
        0,
        {"name1": {"data_type": "String", "string_value": "foo"}},
    )
    queue.write_batch([message_tuple])

    messages = queue.get_messages(message_attributes=["name1"])
    messages[0].get_body().should.equal("test message 1")

    for name, value in message_tuple[3].items():
        dict(messages[0].message_attributes[name]).should.equal(value)


# Has boto3 equivalent
@mock_sqs_deprecated
def test_delete_batch_operation():
    conn = boto.connect_sqs("the_key", "the_secret")
    queue = conn.create_queue("test-queue", visibility_timeout=3)

    conn.send_message_batch(
        queue,
        [
            ("my_first_message", "test message 1", 0),
            ("my_second_message", "test message 2", 0),
            ("my_third_message", "test message 3", 0),
        ],
    )

    messages = queue.get_messages(2)
    queue.delete_message_batch(messages)

    queue.count().should.equal(1)


@mock_sqs
def test_delete_batch_operation_boto3():
    sqs = boto3.resource("sqs", region_name="us-east-1")
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
    queue.attributes["ApproximateNumberOfMessages"].should.equal("1")


# Has boto3 equivalent
@mock_sqs_deprecated
def test_queue_attributes():
    conn = boto.connect_sqs("the_key", "the_secret")

    queue_name = "test-queue"
    visibility_timeout = 3

    queue = conn.create_queue(queue_name, visibility_timeout=visibility_timeout)

    attributes = queue.get_attributes()

    attributes["QueueArn"].should.look_like(
        "arn:aws:sqs:us-east-1:{AccountId}:{name}".format(
            AccountId=ACCOUNT_ID, name=queue_name
        )
    )

    attributes["VisibilityTimeout"].should.look_like(str(visibility_timeout))

    attribute_names = queue.get_attributes().keys()
    attribute_names.should.contain("ApproximateNumberOfMessagesNotVisible")
    attribute_names.should.contain("MessageRetentionPeriod")
    attribute_names.should.contain("ApproximateNumberOfMessagesDelayed")
    attribute_names.should.contain("MaximumMessageSize")
    attribute_names.should.contain("CreatedTimestamp")
    attribute_names.should.contain("ApproximateNumberOfMessages")
    attribute_names.should.contain("ReceiveMessageWaitTimeSeconds")
    attribute_names.should.contain("DelaySeconds")
    attribute_names.should.contain("VisibilityTimeout")
    attribute_names.should.contain("LastModifiedTimestamp")
    attribute_names.should.contain("QueueArn")


@mock_sqs
def test_change_message_visibility_on_old_message_boto3():
    sqs = boto3.resource("sqs", region_name="us-east-1")
    queue = sqs.create_queue(
        QueueName=str(uuid4())[0:6], Attributes={"VisibilityTimeout": "1"}
    )

    queue.send_message(MessageBody="test message 1")

    messages = queue.receive_messages(MaxNumberOfMessages=1)

    messages.should.have.length_of(1)

    original_message = messages[0]

    queue.reload()
    queue.attributes["ApproximateNumberOfMessages"].should.equal("0")

    time.sleep(2)

    queue.reload()
    queue.attributes["ApproximateNumberOfMessages"].should.equal("1")

    messages = queue.receive_messages(MaxNumberOfMessages=1)

    messages.should.have.length_of(1)

    # Docs indicate this should throw an ReceiptHandleIsInvalid, but this is allowed in AWS
    original_message.change_visibility(VisibilityTimeout=100)
    # Docs indicate this should throw a MessageNotInflight, but this is allowed in AWS
    original_message.change_visibility(VisibilityTimeout=100)

    time.sleep(2)

    # Message is not yet available, because of the visibility-timeout
    messages = queue.receive_messages(MaxNumberOfMessages=1)
    messages.should.have.length_of(0)


@mock_sqs
def test_change_message_visibility_on_visible_message_boto3():
    sqs = boto3.resource("sqs", region_name="us-east-1")
    queue = sqs.create_queue(
        QueueName=str(uuid4())[0:6], Attributes={"VisibilityTimeout": "1"}
    )

    queue.send_message(MessageBody="test message")
    messages = queue.receive_messages(MaxNumberOfMessages=1)
    messages.should.have.length_of(1)

    queue.reload()
    queue.attributes["ApproximateNumberOfMessages"].should.equal("0")

    time.sleep(2)

    messages = queue.receive_messages(MaxNumberOfMessages=1)
    messages.should.have.length_of(1)

    messages[0].change_visibility(VisibilityTimeout=100)

    time.sleep(2)

    queue.reload()
    queue.attributes["ApproximateNumberOfMessages"].should.equal("0")


# Has boto3 equivalent
@mock_sqs_deprecated
def test_purge_action():
    conn = boto.sqs.connect_to_region("us-east-1")

    queue = conn.create_queue("new-queue")
    queue.write(queue.new_message("this is another test message"))
    queue.count().should.equal(1)

    queue.purge()

    queue.count().should.equal(0)


@mock_sqs
def test_purge_queue_before_delete_message():
    client = boto3.client("sqs", region_name="us-east-1")

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

    len(receive_resp2.get("Messages", [])).should.equal(1)
    receive_resp2["Messages"][0]["Body"].should.equal("second_message")


# Has boto3 equivalent
@mock_sqs_deprecated
def test_delete_message_after_visibility_timeout():
    VISIBILITY_TIMEOUT = 1
    conn = boto.sqs.connect_to_region("us-east-1")
    new_queue = conn.create_queue("new-queue", visibility_timeout=VISIBILITY_TIMEOUT)

    m1 = Message()
    m1.set_body("Message 1!")
    new_queue.write(m1)

    assert new_queue.count() == 1

    m1_retrieved = new_queue.read()

    time.sleep(VISIBILITY_TIMEOUT + 1)

    m1_retrieved.delete()

    assert new_queue.count() == 0


@mock_sqs
def test_delete_message_after_visibility_timeout_boto3():
    VISIBILITY_TIMEOUT = 1
    sqs = boto3.resource("sqs", region_name="us-east-1")
    queue = sqs.create_queue(
        QueueName=str(uuid4())[0:6],
        Attributes={"VisibilityTimeout ": f"{VISIBILITY_TIMEOUT}"},
    )

    queue.send_message(MessageBody="Message 1!")

    queue.reload()
    queue.attributes["ApproximateNumberOfMessages"].should.equal("1")

    m1_retrieved = queue.receive_messages()[0]

    time.sleep(VISIBILITY_TIMEOUT + 1)

    m1_retrieved.delete()

    queue.reload()
    queue.attributes["ApproximateNumberOfMessages"].should.equal("0")


@mock_sqs
def test_delete_message_errors():
    client = boto3.client("sqs", region_name="us-east-1")
    response = client.create_queue(QueueName=str(uuid4())[0:6])
    queue_url = response["QueueUrl"]
    client.send_message(QueueUrl=queue_url, MessageBody="body")
    response = client.receive_message(QueueUrl=queue_url)
    receipt_handle = response["Messages"][0]["ReceiptHandle"]

    client.delete_message.when.called_with(
        QueueUrl=queue_url + "-not-existing", ReceiptHandle=receipt_handle
    ).should.throw(
        ClientError, "The specified queue does not exist for this wsdl version."
    )

    client.delete_message.when.called_with(
        QueueUrl=queue_url, ReceiptHandle="not-existing"
    ).should.throw(ClientError, "The input receipt handle is invalid.")


@mock_sqs
def test_delete_message_twice_using_same_receipt_handle():
    client = boto3.client("sqs", region_name="us-east-1")
    response = client.create_queue(QueueName=str(uuid4())[0:6])
    queue_url = response["QueueUrl"]

    client.send_message(QueueUrl=queue_url, MessageBody="body")
    response = client.receive_message(QueueUrl=queue_url)
    receipt_handle = response["Messages"][0]["ReceiptHandle"]

    client.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)
    client.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)


@mock_sqs
def test_delete_message_using_old_receipt_handle():
    client = boto3.client("sqs", region_name="us-east-1")
    response = client.create_queue(
        QueueName=str(uuid4())[0:6], Attributes={"VisibilityTimeout": "0"}
    )
    queue_url = response["QueueUrl"]

    client.send_message(QueueUrl=queue_url, MessageBody="body")
    response = client.receive_message(QueueUrl=queue_url)
    receipt_1 = response["Messages"][0]["ReceiptHandle"]

    response = client.receive_message(QueueUrl=queue_url)
    receipt_2 = response["Messages"][0]["ReceiptHandle"]

    receipt_1.shouldnt.equal(receipt_2)

    # Can use an old receipt_handle to delete a message
    client.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_1)
    # Sanity check the message really is gone
    client.receive_message(QueueUrl=queue_url).shouldnt.have.key("Messages")
    # We can delete it again
    client.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_1)

    # Can use the second receipt handle to delete it 'again' - succeeds, as it is idempotent against the message
    client.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_2)


@mock_sqs
def test_send_message_batch():
    client = boto3.client("sqs", region_name="us-east-1")
    response = client.create_queue(
        QueueName=f"{str(uuid4())[0:6]}.fifo", Attributes={"FifoQueue": "true"},
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

    sorted([entry["Id"] for entry in response["Successful"]]).should.equal(
        ["id_1", "id_2"]
    )

    response = client.receive_message(
        QueueUrl=queue_url,
        MaxNumberOfMessages=10,
        MessageAttributeNames=["attribute_name_1", "attribute_name_2"],
        AttributeNames=["MessageDeduplicationId", "MessageGroupId"],
    )

    response["Messages"][0]["Body"].should.equal("body_1")
    response["Messages"][0]["MessageAttributes"].should.equal(
        {"attribute_name_1": {"StringValue": "attribute_value_1", "DataType": "String"}}
    )
    response["Messages"][0]["Attributes"]["MessageGroupId"].should.equal(
        "message_group_id_1"
    )
    response["Messages"][0]["Attributes"]["MessageDeduplicationId"].should.equal(
        "message_deduplication_id_1"
    )
    response["Messages"][1]["Body"].should.equal("body_2")
    response["Messages"][1]["MessageAttributes"].should.equal(
        {"attribute_name_2": {"StringValue": "123", "DataType": "Number"}}
    )
    response["Messages"][1]["Attributes"]["MessageGroupId"].should.equal(
        "message_group_id_2"
    )
    response["Messages"][1]["Attributes"]["MessageDeduplicationId"].should.equal(
        "message_deduplication_id_2"
    )


@mock_sqs
def test_delete_message_batch_with_duplicates():
    client = boto3.client("sqs", region_name="us-east-1")
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


@mock_sqs
def test_delete_message_batch_with_invalid_receipt_id():
    client = boto3.client("sqs", region_name="us-east-1")
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
            "Message": 'The input receipt handle "fake-receipt-handle-1" is not a valid receipt handle.',
        },
        {
            "Id": "fake-receipt-handle-2",
            "SenderFault": True,
            "Code": "ReceiptHandleIsInvalid",
            "Message": 'The input receipt handle "fake-receipt-handle-2" is not a valid receipt handle.',
        },
    ]


@mock_sqs
def test_message_attributes_in_receive_message():
    sqs = boto3.resource("sqs", region_name="us-east-1")
    conn = boto3.client("sqs", region_name="us-east-1")
    q_resp = conn.create_queue(QueueName="test-queue")
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

    messages[0]["MessageAttributes"].should.equal(
        {
            "timestamp": {
                "StringValue": "1493147359900",
                "DataType": "Number.java.lang.Long",
            }
        }
    )

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

    messages[0].get("MessageAttributes").should.equal(None)

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

    messages[0]["MessageAttributes"].should.equal(
        {
            "timestamp": {
                "StringValue": "1493147359900",
                "DataType": "Number.java.lang.Long",
            }
        }
    )


@mock_sqs
def test_send_message_batch_errors():
    client = boto3.client("sqs", region_name="us-east-1")

    response = client.create_queue(QueueName="test-queue")
    queue_url = response["QueueUrl"]

    client.send_message_batch.when.called_with(
        QueueUrl=queue_url + "-not-existing",
        Entries=[{"Id": "id_1", "MessageBody": "body_1"}],
    ).should.throw(
        ClientError, "The specified queue does not exist for this wsdl version."
    )

    client.send_message_batch.when.called_with(
        QueueUrl=queue_url, Entries=[]
    ).should.throw(
        ClientError,
        "There should be at least one SendMessageBatchRequestEntry in the request.",
    )

    client.send_message_batch.when.called_with(
        QueueUrl=queue_url, Entries=[{"Id": "", "MessageBody": "body_1"}]
    ).should.throw(
        ClientError,
        "A batch entry id can only contain alphanumeric characters, "
        "hyphens and underscores. It can be at most 80 letters long.",
    )

    client.send_message_batch.when.called_with(
        QueueUrl=queue_url, Entries=[{"Id": ".!@#$%^&*()+=", "MessageBody": "body_1"}]
    ).should.throw(
        ClientError,
        "A batch entry id can only contain alphanumeric characters, "
        "hyphens and underscores. It can be at most 80 letters long.",
    )

    client.send_message_batch.when.called_with(
        QueueUrl=queue_url, Entries=[{"Id": "i" * 81, "MessageBody": "body_1"}]
    ).should.throw(
        ClientError,
        "A batch entry id can only contain alphanumeric characters, "
        "hyphens and underscores. It can be at most 80 letters long.",
    )

    client.send_message_batch.when.called_with(
        QueueUrl=queue_url, Entries=[{"Id": "id_1", "MessageBody": "b" * 262145}]
    ).should.throw(
        ClientError,
        "Batch requests cannot be longer than 262144 bytes. "
        "You have sent 262145 bytes.",
    )

    # only the first duplicated Id is reported
    client.send_message_batch.when.called_with(
        QueueUrl=queue_url,
        Entries=[
            {"Id": "id_1", "MessageBody": "body_1"},
            {"Id": "id_2", "MessageBody": "body_2"},
            {"Id": "id_2", "MessageBody": "body_2"},
            {"Id": "id_1", "MessageBody": "body_1"},
        ],
    ).should.throw(ClientError, "Id id_2 repeated.")

    entries = [
        {"Id": "id_{}".format(i), "MessageBody": "body_{}".format(i)} for i in range(11)
    ]
    client.send_message_batch.when.called_with(
        QueueUrl=queue_url, Entries=entries
    ).should.throw(
        ClientError,
        "Maximum number of entries per request are 10. " "You have sent 11.",
    )


@mock_sqs
def test_send_message_batch_with_empty_list():
    client = boto3.client("sqs", region_name="us-east-1")

    response = client.create_queue(QueueName="test-queue")
    queue_url = response["QueueUrl"]

    client.send_message_batch.when.called_with(
        QueueUrl=queue_url, Entries=[]
    ).should.throw(
        ClientError,
        "There should be at least one SendMessageBatchRequestEntry in the request.",
    )


@mock_sqs
def test_batch_change_message_visibility():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Cant manipulate time in server mode")

    with freeze_time("2015-01-01 12:00:00"):
        sqs = boto3.client("sqs", region_name="us-east-1")
        resp = sqs.create_queue(
            QueueName="test-dlr-queue.fifo", Attributes={"FifoQueue": "true"}
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
        len(receive_resp["Messages"]).should.equal(2)

        handles = [item["ReceiptHandle"] for item in receive_resp["Messages"]]
        entries = [
            {
                "Id": str(uuid.uuid4()),
                "ReceiptHandle": handle,
                "VisibilityTimeout": 43000,
            }
            for handle in handles
        ]

        resp = sqs.change_message_visibility_batch(QueueUrl=queue_url, Entries=entries)
        len(resp["Successful"]).should.equal(2)

    with freeze_time("2015-01-01 14:00:00"):
        resp = sqs.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=3)
        len(resp["Messages"]).should.equal(1)

    with freeze_time("2015-01-01 16:00:00"):
        resp = sqs.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=3)
        len(resp["Messages"]).should.equal(1)

    with freeze_time("2015-01-02 12:00:00"):
        resp = sqs.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=3)
        len(resp["Messages"]).should.equal(3)


@mock_sqs
def test_batch_change_message_visibility_on_old_message():
    sqs = boto3.resource("sqs", region_name="us-east-1")
    queue = sqs.create_queue(
        QueueName=str(uuid4())[0:6], Attributes={"VisibilityTimeout": "1"}
    )

    queue.send_message(MessageBody="test message 1")

    messages = queue.receive_messages(MaxNumberOfMessages=1)

    messages.should.have.length_of(1)

    original_message = messages[0]

    time.sleep(2)

    messages = queue.receive_messages(MaxNumberOfMessages=1)
    messages[0].receipt_handle.shouldnt.equal(original_message.receipt_handle)

    entries = [
        {
            "Id": str(uuid.uuid4()),
            "ReceiptHandle": original_message.receipt_handle,
            "VisibilityTimeout": 4,
        }
    ]

    resp = queue.change_message_visibility_batch(Entries=entries)
    resp["Successful"].should.have.length_of(1)


@mock_sqs
def test_permissions():
    client = boto3.client("sqs", region_name="us-east-1")

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
    policy["Version"].should.equal("2012-10-17")
    policy["Id"].should.equal(
        f"arn:aws:sqs:us-east-1:123456789012:{q_name}/SQSDefaultPolicy"
    )
    sorted(policy["Statement"], key=lambda x: x["Sid"]).should.equal(
        [
            {
                "Sid": "account1",
                "Effect": "Allow",
                "Principal": {"AWS": "arn:aws:iam::111111111111:root"},
                "Action": "SQS:*",
                "Resource": f"arn:aws:sqs:us-east-1:123456789012:{q_name}",
            },
            {
                "Sid": "account2",
                "Effect": "Allow",
                "Principal": {"AWS": "arn:aws:iam::222211111111:root"},
                "Action": "SQS:SendMessage",
                "Resource": f"arn:aws:sqs:us-east-1:123456789012:{q_name}",
            },
        ]
    )

    client.remove_permission(QueueUrl=queue_url, Label="account2")

    response = client.get_queue_attributes(
        QueueUrl=queue_url, AttributeNames=["Policy"]
    )
    json.loads(response["Attributes"]["Policy"]).should.equal(
        {
            "Version": "2012-10-17",
            "Id": f"arn:aws:sqs:us-east-1:123456789012:{q_name}/SQSDefaultPolicy",
            "Statement": [
                {
                    "Sid": "account1",
                    "Effect": "Allow",
                    "Principal": {"AWS": "arn:aws:iam::111111111111:root"},
                    "Action": "SQS:*",
                    "Resource": f"arn:aws:sqs:us-east-1:123456789012:{q_name}",
                },
            ],
        }
    )


@mock_sqs
def test_get_queue_attributes_template_response_validation():
    client = boto3.client("sqs", region_name="us-east-1")

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


@mock_sqs
def test_add_permission_errors():
    client = boto3.client("sqs", region_name="us-east-1")
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
    ex.operation_name.should.equal("AddPermission")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("InvalidParameterValue")
    ex.response["Error"]["Message"].should.equal(
        "Value test for parameter Label is invalid. " "Reason: Already exists."
    )

    with pytest.raises(ClientError) as e:
        client.add_permission(
            QueueUrl=queue_url,
            Label="test-2",
            AWSAccountIds=["111111111111"],
            Actions=["RemovePermission"],
        )
    ex = e.value
    ex.operation_name.should.equal("AddPermission")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("InvalidParameterValue")
    ex.response["Error"]["Message"].should.equal(
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
    ex.operation_name.should.equal("AddPermission")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("MissingParameter")
    ex.response["Error"]["Message"].should.equal(
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
    ex.operation_name.should.equal("AddPermission")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("InvalidParameterValue")
    ex.response["Error"]["Message"].should.equal(
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
    ex.operation_name.should.equal("AddPermission")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(403)
    ex.response["Error"]["Code"].should.contain("OverLimit")
    ex.response["Error"]["Message"].should.equal(
        "8 Actions were found, maximum allowed is 7."
    )


@mock_sqs
def test_remove_permission_errors():
    client = boto3.client("sqs", region_name="us-east-1")
    response = client.create_queue(QueueName=str(uuid4())[0:6])
    queue_url = response["QueueUrl"]

    with pytest.raises(ClientError) as e:
        client.remove_permission(QueueUrl=queue_url, Label="test")
    ex = e.value
    ex.operation_name.should.equal("RemovePermission")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("InvalidParameterValue")
    ex.response["Error"]["Message"].should.equal(
        "Value test for parameter Label is invalid. "
        "Reason: can't find label on existing policy."
    )


@mock_sqs
def test_tags():
    client = boto3.client("sqs", region_name="us-east-1")

    resp = client.create_queue(
        QueueName="test-dlr-queue.fifo", Attributes={"FifoQueue": "true"}
    )
    queue_url = resp["QueueUrl"]

    client.tag_queue(QueueUrl=queue_url, Tags={"test1": "value1", "test2": "value2"})

    resp = client.list_queue_tags(QueueUrl=queue_url)
    resp["Tags"].should.contain("test1")
    resp["Tags"].should.contain("test2")

    client.untag_queue(QueueUrl=queue_url, TagKeys=["test2"])

    resp = client.list_queue_tags(QueueUrl=queue_url)
    resp["Tags"].should.contain("test1")
    resp["Tags"].should_not.contain("test2")

    # removing a non existing tag should not raise any error
    client.untag_queue(QueueUrl=queue_url, TagKeys=["not-existing-tag"])
    client.list_queue_tags(QueueUrl=queue_url)["Tags"].should.equal({"test1": "value1"})


@mock_sqs
def test_list_queue_tags_errors():
    client = boto3.client("sqs", region_name="us-east-1")

    response = client.create_queue(
        QueueName=str(uuid4())[0:6], tags={"tag_key_1": "tag_value_X"}
    )
    queue_url = response["QueueUrl"]

    client.list_queue_tags.when.called_with(
        QueueUrl=queue_url + "-not-existing"
    ).should.throw(
        ClientError, "The specified queue does not exist for this wsdl version."
    )


@mock_sqs
def test_tag_queue_errors():
    client = boto3.client("sqs", region_name="us-east-1")

    q_name = str(uuid4())[0:6]
    response = client.create_queue(QueueName=q_name, tags={"tag_key_1": "tag_value_X"})
    queue_url = response["QueueUrl"]

    client.tag_queue.when.called_with(
        QueueUrl=queue_url + "-not-existing", Tags={"tag_key_1": "tag_value_1"}
    ).should.throw(
        ClientError, "The specified queue does not exist for this wsdl version."
    )

    client.tag_queue.when.called_with(QueueUrl=queue_url, Tags={}).should.throw(
        ClientError, "The request must contain the parameter Tags."
    )

    too_many_tags = {
        "tag_key_{}".format(i): "tag_value_{}".format(i) for i in range(51)
    }
    client.tag_queue.when.called_with(
        QueueUrl=queue_url, Tags=too_many_tags
    ).should.throw(ClientError, f"Too many tags added for queue {q_name}.")

    # when the request fails, the tags should not be updated
    client.list_queue_tags(QueueUrl=queue_url)["Tags"].should.equal(
        {"tag_key_1": "tag_value_X"}
    )


@mock_sqs
def test_untag_queue_errors():
    client = boto3.client("sqs", region_name="us-east-1")

    response = client.create_queue(
        QueueName=str(uuid4())[0:6], tags={"tag_key_1": "tag_value_1"}
    )
    queue_url = response["QueueUrl"]

    client.untag_queue.when.called_with(
        QueueUrl=queue_url + "-not-existing", TagKeys=["tag_key_1"]
    ).should.throw(
        ClientError, "The specified queue does not exist for this wsdl version."
    )

    client.untag_queue.when.called_with(QueueUrl=queue_url, TagKeys=[]).should.throw(
        ClientError, "Tag keys must be between 1 and 128 characters in length."
    )


@mock_sqs
def test_create_fifo_queue_with_dlq():
    sqs = boto3.client("sqs", region_name="us-east-1")
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


@mock_sqs
def test_queue_with_dlq():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Cant manipulate time in server mode")

    sqs = boto3.client("sqs", region_name="us-east-1")

    with freeze_time("2015-01-01 12:00:00"):
        resp = sqs.create_queue(
            QueueName=f"{str(uuid4())[0:6]}.fifo", Attributes={"FifoQueue": "true"}
        )
        queue_url1 = resp["QueueUrl"]
        queue_arn1 = sqs.get_queue_attributes(
            QueueUrl=queue_url1, AttributeNames=["QueueArn"]
        )["Attributes"]["QueueArn"]

        resp = sqs.create_queue(
            QueueName=f"{str(uuid4())[0:6]}.fifo",
            Attributes={
                "FifoQueue": "true",
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


@mock_sqs
def test_redrive_policy_available():
    sqs = boto3.client("sqs", region_name="us-east-1")

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


@mock_sqs
def test_redrive_policy_non_existent_queue():
    sqs = boto3.client("sqs", region_name="us-east-1")
    redrive_policy = {
        "deadLetterTargetArn": "arn:aws:sqs:us-east-1:{}:no-queue".format(ACCOUNT_ID),
        "maxReceiveCount": 1,
    }

    with pytest.raises(ClientError):
        sqs.create_queue(
            QueueName="test-queue",
            Attributes={"RedrivePolicy": json.dumps(redrive_policy)},
        )


@mock_sqs
def test_redrive_policy_set_attributes():
    sqs = boto3.resource("sqs", region_name="us-east-1")

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


@mock_sqs
def test_redrive_policy_set_attributes_with_string_value():
    sqs = boto3.resource("sqs", region_name="us-east-1")

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


@mock_sqs
def test_receive_messages_with_message_group_id():
    sqs = boto3.resource("sqs", region_name="us-east-1")
    queue = sqs.create_queue(
        QueueName=f"{str(uuid4())[0:6]}.fifo", Attributes={"FifoQueue": "true"}
    )
    queue.set_attributes(Attributes={"VisibilityTimeout": "3600"})
    queue.send_message(MessageBody="message-1", MessageGroupId="group")
    queue.send_message(MessageBody="message-2", MessageGroupId="group")
    queue.send_message(MessageBody="message-3", MessageGroupId="group")
    queue.send_message(MessageBody="separate-message", MessageGroupId="anothergroup")

    messages = queue.receive_messages(
        MaxNumberOfMessages=2, AttributeNames=["MessageGroupId"]
    )
    messages.should.have.length_of(2)
    messages[0].attributes["MessageGroupId"].should.equal("group")

    # Different client can not 'see' messages from the group until they are processed
    messages_for_client_2 = queue.receive_messages(WaitTimeSeconds=0)
    messages_for_client_2.should.have.length_of(1)
    messages_for_client_2[0].body.should.equal("separate-message")

    # message is now processed, next one should be available
    for message in messages:
        message.delete()
    messages = queue.receive_messages()
    messages.should.have.length_of(1)
    messages[0].body.should.equal("message-3")


@mock_sqs
def test_receive_messages_with_message_group_id_on_requeue():
    sqs = boto3.resource("sqs", region_name="us-east-1")
    queue = sqs.create_queue(
        QueueName=f"{str(uuid4())[0:6]}.fifo", Attributes={"FifoQueue": "true"}
    )
    queue.set_attributes(Attributes={"VisibilityTimeout": "3600"})
    queue.send_message(MessageBody="message-1", MessageGroupId="group")
    queue.send_message(MessageBody="message-2", MessageGroupId="group")

    messages = queue.receive_messages()
    messages.should.have.length_of(1)
    message = messages[0]

    # received message is not deleted!

    messages = queue.receive_messages(WaitTimeSeconds=0)
    messages.should.have.length_of(0)

    # message is now available again, next one should be available
    message.change_visibility(VisibilityTimeout=0)
    messages = queue.receive_messages()
    messages.should.have.length_of(1)
    messages[0].message_id.should.equal(message.message_id)


@mock_sqs
def test_receive_messages_with_message_group_id_on_visibility_timeout():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Cant manipulate time in server mode")

    with freeze_time("2015-01-01 12:00:00"):
        sqs = boto3.resource("sqs", region_name="us-east-1")
        queue = sqs.create_queue(
            QueueName="test-queue.fifo", Attributes={"FifoQueue": "true"}
        )
        queue.set_attributes(Attributes={"VisibilityTimeout": "3600"})
        queue.send_message(MessageBody="message-1", MessageGroupId="group")
        queue.send_message(MessageBody="message-2", MessageGroupId="group")

        messages = queue.receive_messages()
        messages.should.have.length_of(1)
        message = messages[0]

        # received message is not processed yet
        messages_for_second_client = queue.receive_messages(WaitTimeSeconds=0)
        messages_for_second_client.should.have.length_of(0)

        for message in messages:
            message.change_visibility(VisibilityTimeout=10)

    with freeze_time("2015-01-01 12:00:05"):
        # no timeout yet
        messages = queue.receive_messages(WaitTimeSeconds=0)
        messages.should.have.length_of(0)

    with freeze_time("2015-01-01 12:00:15"):
        # message is now available again, next one should be available
        messages = queue.receive_messages()
        messages.should.have.length_of(1)
        messages[0].message_id.should.equal(message.message_id)


@mock_sqs
def test_receive_message_for_queue_with_receive_message_wait_time_seconds_set():
    sqs = boto3.resource("sqs", region_name="us-east-1")

    queue = sqs.create_queue(
        QueueName=str(uuid4())[0:6], Attributes={"ReceiveMessageWaitTimeSeconds": "2"}
    )

    queue.receive_messages()


@mock_sqs
def test_list_queues_limits_to_1000_queues():
    if settings.TEST_SERVER_MODE:
        # Re-visit once we have a NextToken-implementation for list_queues
        raise SkipTest("Too many queues for a persistent mode")
    client = boto3.client("sqs", region_name="us-east-1")

    prefix_name = str(uuid4())[0:6]
    queue_urls = []
    for i in range(1001):
        queue = client.create_queue(QueueName=f"{prefix_name}-{i}")
        queue_urls.append(queue["QueueUrl"])

    client.list_queues()["QueueUrls"].should.have.length_of(1000)
    client.list_queues(QueueNamePrefix=prefix_name)["QueueUrls"].should.have.length_of(
        1000
    )

    resource = boto3.resource("sqs", region_name="us-east-1")

    list(resource.queues.all()).should.have.length_of(1000)
    list(resource.queues.filter(QueueNamePrefix=prefix_name)).should.have.length_of(
        1000
    )

    # Delete this again, to not hog all the resources
    for url in queue_urls:
        client.delete_queue(QueueUrl=url)


@mock_sqs
def test_send_message_to_fifo_without_message_group_id():
    sqs = boto3.resource("sqs", region_name="eu-west-3")
    queue = sqs.create_queue(
        QueueName=f"{str(uuid4())[0:6]}.fifo",
        Attributes={"FifoQueue": "true", "ContentBasedDeduplication": "true"},
    )

    with pytest.raises(Exception) as e:
        queue.send_message(MessageBody="message-1")
    ex = e.value
    ex.response["Error"]["Code"].should.equal("MissingParameter")
    ex.response["Error"]["Message"].should.equal(
        "The request must contain the parameter MessageGroupId."
    )


@mock_sqs
def test_send_messages_to_fifo_without_message_group_id():
    sqs = boto3.resource("sqs", region_name="eu-west-3")
    queue = sqs.create_queue(
        QueueName=f"{str(uuid4())[0:6]}.fifo",
        Attributes={"FifoQueue": "true", "ContentBasedDeduplication": "true"},
    )

    with pytest.raises(Exception) as e:
        queue.send_messages(
            Entries=[{"Id": "id_1", "MessageBody": "body_1",},]
        )
    ex = e.value
    ex.response["Error"]["Code"].should.equal("MissingParameter")
    ex.response["Error"]["Message"].should.equal(
        "The request must contain the parameter MessageGroupId."
    )


@mock_sqs
def test_maximum_message_size_attribute_default():
    sqs = boto3.resource("sqs", region_name="eu-west-3")
    queue = sqs.create_queue(QueueName=str(uuid4()),)
    int(queue.attributes["MaximumMessageSize"]).should.equal(MAXIMUM_MESSAGE_LENGTH)
    with pytest.raises(Exception) as e:
        queue.send_message(MessageBody="a" * (MAXIMUM_MESSAGE_LENGTH + 1))
    ex = e.value
    ex.response["Error"]["Code"].should.equal("InvalidParameterValue")


@mock_sqs
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
        ex.response["Error"]["Code"].should.equal("InvalidAttributeValue")


@mock_sqs
def test_send_message_fails_when_message_size_greater_than_max_message_size():
    sqs = boto3.resource("sqs", region_name="eu-west-3")
    message_size_limit = 12345
    queue = sqs.create_queue(
        QueueName=str(uuid4()),
        Attributes={"MaximumMessageSize": str(message_size_limit)},
    )
    int(queue.attributes["MaximumMessageSize"]).should.equal(message_size_limit)
    with pytest.raises(ClientError) as e:
        queue.send_message(MessageBody="a" * (message_size_limit + 1))
    ex = e.value
    ex.response["Error"]["Code"].should.equal("InvalidParameterValue")
    ex.response["Error"]["Message"].should.contain(
        "{} bytes".format(message_size_limit)
    )


@mock_sqs
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

    sqs = boto3.resource("sqs", region_name="us-east-1")
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
    messages.should.have.length_of(expected_count)


@mock_sqs
@pytest.mark.parametrize(
    "msg_1, msg_2, expected_count", [("msg1", "msg1", 1), ("msg1", "msg2", 2),],
)
def test_fifo_queue_deduplication_withoutid(msg_1, msg_2, expected_count):

    sqs = boto3.resource("sqs", region_name="us-east-1")
    q_name = str(uuid4())[0:6]
    msg_queue = sqs.create_queue(
        QueueName=f"{q_name}-dlq.fifo",
        Attributes={"FifoQueue": "true", "ContentBasedDeduplication": "true"},
    )

    msg_queue.send_message(MessageBody=msg_1, MessageGroupId="1")
    msg_queue.send_message(MessageBody=msg_2, MessageGroupId="2")
    messages = msg_queue.receive_messages(MaxNumberOfMessages=2)
    messages.should.have.length_of(expected_count)


@mock.patch(
    "moto.sqs.models.DEDUPLICATION_TIME_IN_SECONDS", MOCK_DEDUPLICATION_TIME_IN_SECONDS
)
@mock_sqs
def test_fifo_queue_send_duplicate_messages_after_deduplication_time_limit():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Cant patch env variables in server mode")

    sqs = boto3.resource("sqs", region_name="us-east-1")
    msg_queue = sqs.create_queue(
        QueueName="test-queue-dlq.fifo",
        Attributes={"FifoQueue": "true", "ContentBasedDeduplication": "true"},
    )

    msg_queue.send_message(MessageBody="first", MessageGroupId="1")
    time.sleep(MOCK_DEDUPLICATION_TIME_IN_SECONDS + 5)
    msg_queue.send_message(MessageBody="first", MessageGroupId="2")
    messages = msg_queue.receive_messages(MaxNumberOfMessages=2)
    messages.should.have.length_of(2)


@mock_sqs
def test_fifo_queue_send_deduplicationid_same_as_sha256_of_old_message():

    sqs = boto3.resource("sqs", region_name="us-east-1")
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
    messages.should.have.length_of(1)


@mock_sqs
def test_fifo_send_message_when_same_group_id_is_in_dlq():

    sqs = boto3.resource("sqs", region_name="us-east-1")
    q_name = f"{str(uuid4())[0:6]}-dlq.fifo"
    dlq = sqs.create_queue(QueueName=q_name, Attributes={"FifoQueue": "true"})

    queue = sqs.get_queue_by_name(QueueName=q_name)
    dead_letter_queue_arn = queue.attributes.get("QueueArn")

    msg_queue = sqs.create_queue(
        QueueName=f"{str(uuid4())[0:6]}.fifo",
        Attributes={
            "FifoQueue": "true",
            "RedrivePolicy": json.dumps(
                {"deadLetterTargetArn": dead_letter_queue_arn, "maxReceiveCount": 1},
            ),
            "VisibilityTimeout": "1",
        },
    )

    msg_queue.send_message(MessageBody="first", MessageGroupId="1")
    messages = msg_queue.receive_messages()
    messages.should.have.length_of(1)

    time.sleep(1.1)

    messages = msg_queue.receive_messages()
    messages.should.have.length_of(0)

    messages = dlq.receive_messages()
    messages.should.have.length_of(1)

    msg_queue.send_message(MessageBody="second", MessageGroupId="1")
    messages = msg_queue.receive_messages()
    messages.should.have.length_of(1)


@mock_sqs
def test_receive_message_should_not_accept_invalid_urls():
    sqs = boto3.resource("sqs", region_name="us-east-1")
    conn = boto3.client("sqs", region_name="us-east-1")
    name = str(uuid4())[0:6]
    q_response = conn.create_queue(QueueName=name)
    working_url = q_response["QueueUrl"]
    # https://queue.amazonaws.com/012341234/test-queue
    # http://localhost:5000/012341234/test-queue in ServerMode
    working_url.should.match(f"/{ACCOUNT_ID}/{name}")

    queue = sqs.Queue(name)
    with pytest.raises(ClientError) as e:
        queue.send_message(MessageBody="this is a test message")
    err = e.value.response["Error"]
    err["Code"].should.equal("InvalidAddress")
    err["Message"].should.equal(f"The address {name} is not valid for this endpoint.")

    with pytest.raises(ClientError) as e:
        conn.receive_message(QueueUrl=name)
    err = e.value.response["Error"]
    err["Code"].should.equal("InvalidAddress")
    err["Message"].should.equal(f"The address {name} is not valid for this endpoint.")


@mock_sqs
def test_message_attributes_contains_trace_header():
    sqs = boto3.resource("sqs", region_name="us-east-1")
    conn = boto3.client("sqs", region_name="us-east-1")
    q_name = str(uuid4())[0:6]
    q_resp = conn.create_queue(QueueName=q_name)
    queue = sqs.Queue(q_resp["QueueUrl"])
    body_one = "this is a test message"

    queue.send_message(
        MessageBody=body_one,
        MessageSystemAttributes={
            "AWSTraceHeader": {
                "StringValue": "Root=1-3152b799-8954dae64eda91bc9a23a7e8;Parent=7fa8c0f79203be72;Sampled=1",
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


@mock_sqs
def test_receive_message_again_preserves_attributes():
    sqs = boto3.resource("sqs", region_name="us-east-1")
    conn = boto3.client("sqs", region_name="us-east-1")
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
        QueueUrl=queue.url, MaxNumberOfMessages=2, MessageAttributeNames=["All"],
    )["Messages"]
    assert len(second_messages[0]["MessageAttributes"]) == 2
    assert second_messages[0]["MessageAttributes"].get("Custom1") is not None
    assert second_messages[0]["MessageAttributes"].get("Custom2") is not None


@mock_sqs
def test_message_has_windows_return():
    sqs = boto3.resource("sqs", region_name="us-east-1")
    queue = sqs.create_queue(QueueName=f"{str(uuid4())[0:6]}")

    message = "content:\rmessage_with line"
    queue.send_message(MessageBody=message)

    messages = queue.receive_messages()
    messages.should.have.length_of(1)
    messages[0].body.should.match(message)
