# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os

import boto
import boto3
import botocore.exceptions
from botocore.exceptions import ClientError
from boto.exception import SQSError
from boto.sqs.message import RawMessage, Message

from freezegun import freeze_time
import base64
import json
import sure  # noqa
import time
import uuid

from moto import settings, mock_sqs, mock_sqs_deprecated
from tests.helpers import requires_boto_gte
import tests.backport_assert_raises  # noqa
from nose.tools import assert_raises
from nose import SkipTest


@mock_sqs
def test_create_fifo_queue_fail():
    sqs = boto3.client('sqs', region_name='us-east-1')

    try:
        sqs.create_queue(
            QueueName='test-queue',
            Attributes={
                'FifoQueue': 'true',
            }
        )
    except botocore.exceptions.ClientError as err:
        err.response['Error']['Code'].should.equal('InvalidParameterValue')
    else:
        raise RuntimeError('Should of raised InvalidParameterValue Exception')


@mock_sqs
def test_create_queue_with_same_attributes():
    sqs = boto3.client('sqs', region_name='us-east-1')

    dlq_url = sqs.create_queue(QueueName='test-queue-dlq')['QueueUrl']
    dlq_arn = sqs.get_queue_attributes(QueueUrl=dlq_url)['Attributes']['QueueArn']

    attributes = {
        'DelaySeconds': '900',
        'MaximumMessageSize': '262144',
        'MessageRetentionPeriod': '1209600',
        'ReceiveMessageWaitTimeSeconds': '20',
        'RedrivePolicy': '{"deadLetterTargetArn": "%s", "maxReceiveCount": 100}' % (dlq_arn),
        'VisibilityTimeout': '43200'
    }

    sqs.create_queue(
        QueueName='test-queue',
        Attributes=attributes
    )

    sqs.create_queue(
        QueueName='test-queue',
        Attributes=attributes
    )


@mock_sqs
def test_create_queue_with_different_attributes_fail():
    sqs = boto3.client('sqs', region_name='us-east-1')

    sqs.create_queue(
        QueueName='test-queue',
        Attributes={
            'VisibilityTimeout': '10',
        }
    )
    try:
        sqs.create_queue(
            QueueName='test-queue',
            Attributes={
                'VisibilityTimeout': '60',
            }
        )
    except botocore.exceptions.ClientError as err:
        err.response['Error']['Code'].should.equal('QueueAlreadyExists')
    else:
        raise RuntimeError('Should of raised QueueAlreadyExists Exception')


@mock_sqs
def test_create_fifo_queue():
    sqs = boto3.client('sqs', region_name='us-east-1')
    resp = sqs.create_queue(
        QueueName='test-queue.fifo',
        Attributes={
            'FifoQueue': 'true',
        }
    )
    queue_url = resp['QueueUrl']

    response = sqs.get_queue_attributes(QueueUrl=queue_url)
    response['Attributes'].should.contain('FifoQueue')
    response['Attributes']['FifoQueue'].should.equal('true')


@mock_sqs
def test_create_queue():
    sqs = boto3.resource('sqs', region_name='us-east-1')

    new_queue = sqs.create_queue(QueueName='test-queue')
    new_queue.should_not.be.none
    new_queue.should.have.property('url').should.contain('test-queue')

    queue = sqs.get_queue_by_name(QueueName='test-queue')
    queue.attributes.get('QueueArn').should_not.be.none
    queue.attributes.get('QueueArn').split(':')[-1].should.equal('test-queue')
    queue.attributes.get('QueueArn').split(':')[3].should.equal('us-east-1')
    queue.attributes.get('VisibilityTimeout').should_not.be.none
    queue.attributes.get('VisibilityTimeout').should.equal('30')


@mock_sqs
def test_create_queue_kms():
    sqs = boto3.resource('sqs', region_name='us-east-1')

    new_queue = sqs.create_queue(
        QueueName='test-queue',
        Attributes={
            'KmsMasterKeyId': 'master-key-id',
            'KmsDataKeyReusePeriodSeconds': '600'
        })
    new_queue.should_not.be.none

    queue = sqs.get_queue_by_name(QueueName='test-queue')

    queue.attributes.get('KmsMasterKeyId').should.equal('master-key-id')
    queue.attributes.get('KmsDataKeyReusePeriodSeconds').should.equal('600')


@mock_sqs
def test_get_nonexistent_queue():
    sqs = boto3.resource('sqs', region_name='us-east-1')
    with assert_raises(ClientError) as err:
        sqs.get_queue_by_name(QueueName='nonexisting-queue')
    ex = err.exception
    ex.operation_name.should.equal('GetQueueUrl')
    ex.response['Error']['Code'].should.equal(
        'AWS.SimpleQueueService.NonExistentQueue')

    with assert_raises(ClientError) as err:
        sqs.Queue('http://whatever-incorrect-queue-address').load()
    ex = err.exception
    ex.operation_name.should.equal('GetQueueAttributes')
    ex.response['Error']['Code'].should.equal(
        'AWS.SimpleQueueService.NonExistentQueue')


@mock_sqs
def test_message_send_without_attributes():
    sqs = boto3.resource('sqs', region_name='us-east-1')
    queue = sqs.create_queue(QueueName="blah")
    msg = queue.send_message(
        MessageBody="derp"
    )
    msg.get('MD5OfMessageBody').should.equal(
        '58fd9edd83341c29f1aebba81c31e257')
    msg.shouldnt.have.key('MD5OfMessageAttributes')
    msg.get('MessageId').should_not.contain(' \n')

    messages = queue.receive_messages()
    messages.should.have.length_of(1)


@mock_sqs
def test_message_send_with_attributes():
    sqs = boto3.resource('sqs', region_name='us-east-1')
    queue = sqs.create_queue(QueueName="blah")
    msg = queue.send_message(
        MessageBody="derp",
        MessageAttributes={
            'timestamp': {
                'StringValue': '1493147359900',
                'DataType': 'Number',
            }
        }
    )
    msg.get('MD5OfMessageBody').should.equal(
        '58fd9edd83341c29f1aebba81c31e257')
    msg.get('MD5OfMessageAttributes').should.equal(
        '235c5c510d26fb653d073faed50ae77c')
    msg.get('MessageId').should_not.contain(' \n')

    messages = queue.receive_messages()
    messages.should.have.length_of(1)


@mock_sqs
def test_message_with_complex_attributes():
    sqs = boto3.resource('sqs', region_name='us-east-1')
    queue = sqs.create_queue(QueueName="blah")
    msg = queue.send_message(
        MessageBody="derp",
        MessageAttributes={
            'ccc': {'StringValue': 'testjunk', 'DataType': 'String'},
            'aaa': {'BinaryValue': b'\x02\x03\x04', 'DataType': 'Binary'},
            'zzz': {'DataType': 'Number', 'StringValue': '0230.01'},
            'öther_encodings': {'DataType': 'String', 'StringValue': 'T\xFCst'}
        }
    )
    msg.get('MD5OfMessageBody').should.equal(
        '58fd9edd83341c29f1aebba81c31e257')
    msg.get('MD5OfMessageAttributes').should.equal(
        '8ae21a7957029ef04146b42aeaa18a22')
    msg.get('MessageId').should_not.contain(' \n')

    messages = queue.receive_messages()
    messages.should.have.length_of(1)


@mock_sqs
def test_send_message_with_message_group_id():
    sqs = boto3.resource('sqs', region_name='us-east-1')
    queue = sqs.create_queue(QueueName="test-group-id.fifo",
                             Attributes={'FifoQueue': 'true'})

    sent = queue.send_message(
        MessageBody="mydata",
        MessageDeduplicationId="dedupe_id_1",
        MessageGroupId="group_id_1",
    )

    messages = queue.receive_messages()
    messages.should.have.length_of(1)

    message_attributes = messages[0].attributes
    message_attributes.should.contain('MessageGroupId')
    message_attributes['MessageGroupId'].should.equal('group_id_1')
    message_attributes.should.contain('MessageDeduplicationId')
    message_attributes['MessageDeduplicationId'].should.equal('dedupe_id_1')


@mock_sqs
def test_send_message_with_unicode_characters():
    body_one = 'Héllo!😀'

    sqs = boto3.resource('sqs', region_name='us-east-1')
    queue = sqs.create_queue(QueueName="blah")
    msg = queue.send_message(MessageBody=body_one)

    messages = queue.receive_messages()
    message_body = messages[0].body

    message_body.should.equal(body_one)


@mock_sqs
def test_set_queue_attributes():
    sqs = boto3.resource('sqs', region_name='us-east-1')
    queue = sqs.create_queue(QueueName="blah")

    queue.attributes['VisibilityTimeout'].should.equal("30")

    queue.set_attributes(Attributes={"VisibilityTimeout": "45"})
    queue.attributes['VisibilityTimeout'].should.equal("45")


@mock_sqs
def test_create_queues_in_multiple_region():
    west1_conn = boto3.client('sqs', region_name='us-west-1')
    west1_conn.create_queue(QueueName="blah")

    west2_conn = boto3.client('sqs', region_name='us-west-2')
    west2_conn.create_queue(QueueName="test-queue")

    list(west1_conn.list_queues()['QueueUrls']).should.have.length_of(1)
    list(west2_conn.list_queues()['QueueUrls']).should.have.length_of(1)

    if settings.TEST_SERVER_MODE:
        base_url = 'http://localhost:5000'
    else:
        base_url = 'https://us-west-1.queue.amazonaws.com'

    west1_conn.list_queues()['QueueUrls'][0].should.equal(
        '{base_url}/123456789012/blah'.format(base_url=base_url))


@mock_sqs
def test_get_queue_with_prefix():
    conn = boto3.client("sqs", region_name='us-west-1')
    conn.create_queue(QueueName="prefixa-queue")
    conn.create_queue(QueueName="prefixb-queue")
    conn.create_queue(QueueName="test-queue")

    conn.list_queues()['QueueUrls'].should.have.length_of(3)

    queue = conn.list_queues(QueueNamePrefix="test-")['QueueUrls']
    queue.should.have.length_of(1)

    if settings.TEST_SERVER_MODE:
        base_url = 'http://localhost:5000'
    else:
        base_url = 'https://us-west-1.queue.amazonaws.com'

    queue[0].should.equal(
        "{base_url}/123456789012/test-queue".format(base_url=base_url))


@mock_sqs
def test_delete_queue():
    sqs = boto3.resource('sqs', region_name='us-east-1')
    conn = boto3.client("sqs", region_name='us-east-1')
    conn.create_queue(QueueName="test-queue",
                      Attributes={"VisibilityTimeout": "3"})
    queue = sqs.Queue('test-queue')

    conn.list_queues()['QueueUrls'].should.have.length_of(1)

    queue.delete()
    conn.list_queues().get('QueueUrls').should.equal(None)

    with assert_raises(botocore.exceptions.ClientError):
        queue.delete()


@mock_sqs
def test_set_queue_attribute():
    sqs = boto3.resource('sqs', region_name='us-east-1')
    conn = boto3.client("sqs", region_name='us-east-1')
    conn.create_queue(QueueName="test-queue",
                      Attributes={"VisibilityTimeout": '3'})

    queue = sqs.Queue("test-queue")
    queue.attributes['VisibilityTimeout'].should.equal('3')

    queue.set_attributes(Attributes={"VisibilityTimeout": '45'})
    queue = sqs.Queue("test-queue")
    queue.attributes['VisibilityTimeout'].should.equal('45')


@mock_sqs
def test_send_receive_message_without_attributes():
    sqs = boto3.resource('sqs', region_name='us-east-1')
    conn = boto3.client("sqs", region_name='us-east-1')
    conn.create_queue(QueueName="test-queue")
    queue = sqs.Queue("test-queue")

    body_one = 'this is a test message'
    body_two = 'this is another test message'

    queue.send_message(MessageBody=body_one)
    queue.send_message(MessageBody=body_two)

    messages = conn.receive_message(
        QueueUrl=queue.url, MaxNumberOfMessages=2)['Messages']

    message1 = messages[0]
    message2 = messages[1]

    message1['Body'].should.equal(body_one)
    message2['Body'].should.equal(body_two)

    message1.shouldnt.have.key('MD5OfMessageAttributes')
    message2.shouldnt.have.key('MD5OfMessageAttributes')


@mock_sqs
def test_send_receive_message_with_attributes():
    sqs = boto3.resource('sqs', region_name='us-east-1')
    conn = boto3.client("sqs", region_name='us-east-1')
    conn.create_queue(QueueName="test-queue")
    queue = sqs.Queue("test-queue")

    body_one = 'this is a test message'
    body_two = 'this is another test message'

    queue.send_message(
        MessageBody=body_one,
        MessageAttributes={
            'timestamp': {
                'StringValue': '1493147359900',
                'DataType': 'Number',
            }
        }
    )

    queue.send_message(
        MessageBody=body_two,
        MessageAttributes={
            'timestamp': {
                'StringValue': '1493147359901',
                'DataType': 'Number',
            }
        }
    )

    messages = conn.receive_message(
        QueueUrl=queue.url, MaxNumberOfMessages=2)['Messages']

    message1 = messages[0]
    message2 = messages[1]

    message1.get('Body').should.equal(body_one)
    message2.get('Body').should.equal(body_two)

    message1.get('MD5OfMessageAttributes').should.equal('235c5c510d26fb653d073faed50ae77c')
    message2.get('MD5OfMessageAttributes').should.equal('994258b45346a2cc3f9cbb611aa7af30')


@mock_sqs
def test_send_receive_message_timestamps():
    sqs = boto3.resource('sqs', region_name='us-east-1')
    conn = boto3.client("sqs", region_name='us-east-1')
    conn.create_queue(QueueName="test-queue")
    queue = sqs.Queue("test-queue")

    response = queue.send_message(MessageBody="derp")
    assert response['ResponseMetadata']['RequestId']

    messages = conn.receive_message(
        QueueUrl=queue.url, MaxNumberOfMessages=1)['Messages']

    message = messages[0]
    sent_timestamp = message.get('Attributes').get('SentTimestamp')
    approximate_first_receive_timestamp = message.get('Attributes').get('ApproximateFirstReceiveTimestamp')

    int.when.called_with(sent_timestamp).shouldnt.throw(ValueError)
    int.when.called_with(approximate_first_receive_timestamp).shouldnt.throw(ValueError)


@mock_sqs
def test_max_number_of_messages_invalid_param():
    sqs = boto3.resource('sqs', region_name='us-east-1')
    queue = sqs.create_queue(QueueName='test-queue')

    with assert_raises(ClientError):
        queue.receive_messages(MaxNumberOfMessages=11)

    with assert_raises(ClientError):
        queue.receive_messages(MaxNumberOfMessages=0)

    # no error but also no messages returned
    queue.receive_messages(MaxNumberOfMessages=1, WaitTimeSeconds=0)


@mock_sqs
def test_wait_time_seconds_invalid_param():
    sqs = boto3.resource('sqs', region_name='us-east-1')
    queue = sqs.create_queue(QueueName='test-queue')

    with assert_raises(ClientError):
        queue.receive_messages(WaitTimeSeconds=-1)

    with assert_raises(ClientError):
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

    sqs = boto3.resource('sqs', region_name='us-east-1')
    queue = sqs.create_queue(QueueName="blah")

    messages = queue.receive_messages(WaitTimeSeconds=0)
    messages.should.equal([])


@mock_sqs_deprecated
def test_send_message_with_xml_characters():
    conn = boto.connect_sqs('the_key', 'the_secret')
    queue = conn.create_queue("test-queue", visibility_timeout=3)
    queue.set_message_class(RawMessage)

    body_one = '< & >'

    queue.write(queue.new_message(body_one))

    messages = conn.receive_message(queue, number_messages=1)

    messages[0].get_body().should.equal(body_one)


@requires_boto_gte("2.28")
@mock_sqs_deprecated
def test_send_message_with_attributes():
    conn = boto.connect_sqs('the_key', 'the_secret')
    queue = conn.create_queue("test-queue", visibility_timeout=3)
    queue.set_message_class(RawMessage)

    body = 'this is a test message'
    message = queue.new_message(body)
    BASE64_BINARY = base64.b64encode(b'binary value').decode('utf-8')
    message_attributes = {
        'test.attribute_name': {'data_type': 'String', 'string_value': 'attribute value'},
        'test.binary_attribute': {'data_type': 'Binary', 'binary_value': BASE64_BINARY},
        'test.number_attribute': {'data_type': 'Number', 'string_value': 'string value'}
    }
    message.message_attributes = message_attributes

    queue.write(message)

    messages = conn.receive_message(queue)

    messages[0].get_body().should.equal(body)

    for name, value in message_attributes.items():
        dict(messages[0].message_attributes[name]).should.equal(value)


@mock_sqs_deprecated
def test_send_message_with_delay():
    conn = boto.connect_sqs('the_key', 'the_secret')
    queue = conn.create_queue("test-queue", visibility_timeout=3)
    queue.set_message_class(RawMessage)

    body_one = 'this is a test message'
    body_two = 'this is another test message'

    queue.write(queue.new_message(body_one), delay_seconds=3)
    queue.write(queue.new_message(body_two))

    queue.count().should.equal(1)

    messages = conn.receive_message(queue, number_messages=2)
    assert len(messages) == 1
    message = messages[0]
    assert message.get_body().should.equal(body_two)
    queue.count().should.equal(0)


@mock_sqs_deprecated
def test_send_large_message_fails():
    conn = boto.connect_sqs('the_key', 'the_secret')
    queue = conn.create_queue("test-queue", visibility_timeout=3)
    queue.set_message_class(RawMessage)

    body_one = 'test message' * 200000
    huge_message = queue.new_message(body_one)

    queue.write.when.called_with(huge_message).should.throw(SQSError)


@mock_sqs_deprecated
def test_message_becomes_inflight_when_received():
    conn = boto.connect_sqs('the_key', 'the_secret')
    queue = conn.create_queue("test-queue", visibility_timeout=2)
    queue.set_message_class(RawMessage)

    body_one = 'this is a test message'
    queue.write(queue.new_message(body_one))
    queue.count().should.equal(1)

    messages = conn.receive_message(queue, number_messages=1)
    queue.count().should.equal(0)

    assert len(messages) == 1

    # Wait
    time.sleep(3)

    queue.count().should.equal(1)


@mock_sqs_deprecated
def test_receive_message_with_explicit_visibility_timeout():
    conn = boto.connect_sqs('the_key', 'the_secret')
    queue = conn.create_queue("test-queue", visibility_timeout=3)
    queue.set_message_class(RawMessage)

    body_one = 'this is another test message'
    queue.write(queue.new_message(body_one))

    queue.count().should.equal(1)
    messages = conn.receive_message(
        queue, number_messages=1, visibility_timeout=0)

    assert len(messages) == 1

    # Message should remain visible
    queue.count().should.equal(1)


@mock_sqs_deprecated
def test_change_message_visibility():
    conn = boto.connect_sqs('the_key', 'the_secret')
    queue = conn.create_queue("test-queue", visibility_timeout=2)
    queue.set_message_class(RawMessage)

    body_one = 'this is another test message'
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


@mock_sqs_deprecated
def test_message_attributes():
    conn = boto.connect_sqs('the_key', 'the_secret')
    queue = conn.create_queue("test-queue", visibility_timeout=2)
    queue.set_message_class(RawMessage)

    body_one = 'this is another test message'
    queue.write(queue.new_message(body_one))

    queue.count().should.equal(1)

    messages = conn.receive_message(queue, number_messages=1)
    queue.count().should.equal(0)

    assert len(messages) == 1

    message_attributes = messages[0].attributes

    assert message_attributes.get('ApproximateFirstReceiveTimestamp')
    assert int(message_attributes.get('ApproximateReceiveCount')) == 1
    assert message_attributes.get('SentTimestamp')
    assert message_attributes.get('SenderId')


@mock_sqs_deprecated
def test_read_message_from_queue():
    conn = boto.connect_sqs()
    queue = conn.create_queue('testqueue')
    queue.set_message_class(RawMessage)

    body = 'foo bar baz'
    queue.write(queue.new_message(body))
    message = queue.read(1)
    message.get_body().should.equal(body)


@mock_sqs_deprecated
def test_queue_length():
    conn = boto.connect_sqs('the_key', 'the_secret')
    queue = conn.create_queue("test-queue", visibility_timeout=3)
    queue.set_message_class(RawMessage)

    queue.write(queue.new_message('this is a test message'))
    queue.write(queue.new_message('this is another test message'))
    queue.count().should.equal(2)


@mock_sqs_deprecated
def test_delete_message():
    conn = boto.connect_sqs('the_key', 'the_secret')
    queue = conn.create_queue("test-queue", visibility_timeout=3)
    queue.set_message_class(RawMessage)

    queue.write(queue.new_message('this is a test message'))
    queue.write(queue.new_message('this is another test message'))
    queue.count().should.equal(2)

    messages = conn.receive_message(queue, number_messages=1)
    assert len(messages) == 1
    messages[0].delete()
    queue.count().should.equal(1)

    messages = conn.receive_message(queue, number_messages=1)
    assert len(messages) == 1
    messages[0].delete()
    queue.count().should.equal(0)


@mock_sqs_deprecated
def test_send_batch_operation():
    conn = boto.connect_sqs('the_key', 'the_secret')
    queue = conn.create_queue("test-queue", visibility_timeout=3)

    # See https://github.com/boto/boto/issues/831
    queue.set_message_class(RawMessage)

    queue.write_batch([
        ("my_first_message", 'test message 1', 0),
        ("my_second_message", 'test message 2', 0),
        ("my_third_message", 'test message 3', 0),
    ])

    messages = queue.get_messages(3)
    messages[0].get_body().should.equal("test message 1")

    # Test that pulling more messages doesn't break anything
    messages = queue.get_messages(2)


@requires_boto_gte("2.28")
@mock_sqs_deprecated
def test_send_batch_operation_with_message_attributes():
    conn = boto.connect_sqs('the_key', 'the_secret')
    queue = conn.create_queue("test-queue", visibility_timeout=3)
    queue.set_message_class(RawMessage)

    message_tuple = ("my_first_message", 'test message 1', 0, {
                     'name1': {'data_type': 'String', 'string_value': 'foo'}})
    queue.write_batch([message_tuple])

    messages = queue.get_messages()
    messages[0].get_body().should.equal("test message 1")

    for name, value in message_tuple[3].items():
        dict(messages[0].message_attributes[name]).should.equal(value)


@mock_sqs_deprecated
def test_delete_batch_operation():
    conn = boto.connect_sqs('the_key', 'the_secret')
    queue = conn.create_queue("test-queue", visibility_timeout=3)

    conn.send_message_batch(queue, [
        ("my_first_message", 'test message 1', 0),
        ("my_second_message", 'test message 2', 0),
        ("my_third_message", 'test message 3', 0),
    ])

    messages = queue.get_messages(2)
    queue.delete_message_batch(messages)

    queue.count().should.equal(1)


@mock_sqs_deprecated
def test_queue_attributes():
    conn = boto.connect_sqs('the_key', 'the_secret')

    queue_name = 'test-queue'
    visibility_timeout = 3

    queue = conn.create_queue(
        queue_name, visibility_timeout=visibility_timeout)

    attributes = queue.get_attributes()

    attributes['QueueArn'].should.look_like(
        'arn:aws:sqs:us-east-1:123456789012:%s' % queue_name)

    attributes['VisibilityTimeout'].should.look_like(str(visibility_timeout))

    attribute_names = queue.get_attributes().keys()
    attribute_names.should.contain('ApproximateNumberOfMessagesNotVisible')
    attribute_names.should.contain('MessageRetentionPeriod')
    attribute_names.should.contain('ApproximateNumberOfMessagesDelayed')
    attribute_names.should.contain('MaximumMessageSize')
    attribute_names.should.contain('CreatedTimestamp')
    attribute_names.should.contain('ApproximateNumberOfMessages')
    attribute_names.should.contain('ReceiveMessageWaitTimeSeconds')
    attribute_names.should.contain('DelaySeconds')
    attribute_names.should.contain('VisibilityTimeout')
    attribute_names.should.contain('LastModifiedTimestamp')
    attribute_names.should.contain('QueueArn')


@mock_sqs_deprecated
def test_change_message_visibility_on_invalid_receipt():
    conn = boto.connect_sqs('the_key', 'the_secret')
    queue = conn.create_queue("test-queue", visibility_timeout=1)
    queue.set_message_class(RawMessage)

    queue.write(queue.new_message('this is another test message'))
    queue.count().should.equal(1)
    messages = conn.receive_message(queue, number_messages=1)

    assert len(messages) == 1

    original_message = messages[0]

    queue.count().should.equal(0)

    time.sleep(2)

    queue.count().should.equal(1)

    messages = conn.receive_message(queue, number_messages=1)

    assert len(messages) == 1

    original_message.change_visibility.when.called_with(
        100).should.throw(SQSError)


@mock_sqs_deprecated
def test_change_message_visibility_on_visible_message():
    conn = boto.connect_sqs('the_key', 'the_secret')
    queue = conn.create_queue("test-queue", visibility_timeout=1)
    queue.set_message_class(RawMessage)

    queue.write(queue.new_message('this is another test message'))
    queue.count().should.equal(1)
    messages = conn.receive_message(queue, number_messages=1)

    assert len(messages) == 1

    original_message = messages[0]

    queue.count().should.equal(0)

    time.sleep(2)

    queue.count().should.equal(1)

    original_message.change_visibility.when.called_with(
        100).should.throw(SQSError)


@mock_sqs_deprecated
def test_purge_action():
    conn = boto.sqs.connect_to_region("us-east-1")

    queue = conn.create_queue('new-queue')
    queue.write(queue.new_message('this is another test message'))
    queue.count().should.equal(1)

    queue.purge()

    queue.count().should.equal(0)


@mock_sqs_deprecated
def test_delete_message_after_visibility_timeout():
    VISIBILITY_TIMEOUT = 1
    conn = boto.sqs.connect_to_region("us-east-1")
    new_queue = conn.create_queue(
        'new-queue', visibility_timeout=VISIBILITY_TIMEOUT)

    m1 = Message()
    m1.set_body('Message 1!')
    new_queue.write(m1)

    assert new_queue.count() == 1

    m1_retrieved = new_queue.read()

    time.sleep(VISIBILITY_TIMEOUT + 1)

    m1_retrieved.delete()

    assert new_queue.count() == 0


@mock_sqs
def test_batch_change_message_visibility():
    if os.environ.get('TEST_SERVER_MODE', 'false').lower() == 'true':
        raise SkipTest('Cant manipulate time in server mode')

    with freeze_time("2015-01-01 12:00:00"):
        sqs = boto3.client('sqs', region_name='us-east-1')
        resp = sqs.create_queue(
            QueueName='test-dlr-queue.fifo',
            Attributes={'FifoQueue': 'true'}
        )
        queue_url = resp['QueueUrl']

        sqs.send_message(QueueUrl=queue_url, MessageBody='msg1')
        sqs.send_message(QueueUrl=queue_url, MessageBody='msg2')
        sqs.send_message(QueueUrl=queue_url, MessageBody='msg3')

    with freeze_time("2015-01-01 12:01:00"):
        receive_resp = sqs.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=2)
        len(receive_resp['Messages']).should.equal(2)

        handles = [item['ReceiptHandle'] for item in receive_resp['Messages']]
        entries = [{'Id': str(uuid.uuid4()), 'ReceiptHandle': handle, 'VisibilityTimeout': 43200} for handle in handles]

        resp = sqs.change_message_visibility_batch(QueueUrl=queue_url, Entries=entries)
        len(resp['Successful']).should.equal(2)

    with freeze_time("2015-01-01 14:00:00"):
        resp = sqs.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=3)
        len(resp['Messages']).should.equal(1)

    with freeze_time("2015-01-01 16:00:00"):
        resp = sqs.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=3)
        len(resp['Messages']).should.equal(1)

    with freeze_time("2015-01-02 12:00:00"):
        resp = sqs.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=3)
        len(resp['Messages']).should.equal(3)


@mock_sqs
def test_permissions():
    client = boto3.client('sqs', region_name='us-east-1')

    resp = client.create_queue(
        QueueName='test-dlr-queue.fifo',
        Attributes={'FifoQueue': 'true'}
    )
    queue_url = resp['QueueUrl']

    client.add_permission(QueueUrl=queue_url, Label='account1', AWSAccountIds=['111111111111'], Actions=['*'])
    client.add_permission(QueueUrl=queue_url, Label='account2', AWSAccountIds=['222211111111'], Actions=['SendMessage'])

    with assert_raises(ClientError):
        client.add_permission(QueueUrl=queue_url, Label='account2', AWSAccountIds=['222211111111'], Actions=['SomeRubbish'])

    client.remove_permission(QueueUrl=queue_url, Label='account2')

    with assert_raises(ClientError):
        client.remove_permission(QueueUrl=queue_url, Label='non_existant')


@mock_sqs
def test_tags():
    client = boto3.client('sqs', region_name='us-east-1')

    resp = client.create_queue(
        QueueName='test-dlr-queue.fifo',
        Attributes={'FifoQueue': 'true'}
    )
    queue_url = resp['QueueUrl']

    client.tag_queue(
        QueueUrl=queue_url,
        Tags={
            'test1': 'value1',
            'test2': 'value2',
        }
    )

    resp = client.list_queue_tags(QueueUrl=queue_url)
    resp['Tags'].should.contain('test1')
    resp['Tags'].should.contain('test2')

    client.untag_queue(
        QueueUrl=queue_url,
        TagKeys=['test2']
    )

    resp = client.list_queue_tags(QueueUrl=queue_url)
    resp['Tags'].should.contain('test1')
    resp['Tags'].should_not.contain('test2')


@mock_sqs
def test_create_fifo_queue_with_dlq():
    sqs = boto3.client('sqs', region_name='us-east-1')
    resp = sqs.create_queue(
        QueueName='test-dlr-queue.fifo',
        Attributes={'FifoQueue': 'true'}
    )
    queue_url1 = resp['QueueUrl']
    queue_arn1 = sqs.get_queue_attributes(QueueUrl=queue_url1)['Attributes']['QueueArn']

    resp = sqs.create_queue(
        QueueName='test-dlr-queue',
        Attributes={'FifoQueue': 'false'}
    )
    queue_url2 = resp['QueueUrl']
    queue_arn2 = sqs.get_queue_attributes(QueueUrl=queue_url2)['Attributes']['QueueArn']

    sqs.create_queue(
        QueueName='test-queue.fifo',
        Attributes={
            'FifoQueue': 'true',
            'RedrivePolicy': json.dumps({'deadLetterTargetArn': queue_arn1, 'maxReceiveCount': 2})
        }
    )

    # Cant have fifo queue with non fifo DLQ
    with assert_raises(ClientError):
        sqs.create_queue(
            QueueName='test-queue2.fifo',
            Attributes={
                'FifoQueue': 'true',
                'RedrivePolicy': json.dumps({'deadLetterTargetArn': queue_arn2, 'maxReceiveCount': 2})
            }
        )


@mock_sqs
def test_queue_with_dlq():
    if os.environ.get('TEST_SERVER_MODE', 'false').lower() == 'true':
        raise SkipTest('Cant manipulate time in server mode')

    sqs = boto3.client('sqs', region_name='us-east-1')

    with freeze_time("2015-01-01 12:00:00"):
        resp = sqs.create_queue(
            QueueName='test-dlr-queue.fifo',
            Attributes={'FifoQueue': 'true'}
        )
        queue_url1 = resp['QueueUrl']
        queue_arn1 = sqs.get_queue_attributes(QueueUrl=queue_url1)['Attributes']['QueueArn']

        resp = sqs.create_queue(
            QueueName='test-queue.fifo',
            Attributes={
                'FifoQueue': 'true',
                'RedrivePolicy': json.dumps({'deadLetterTargetArn': queue_arn1, 'maxReceiveCount': 2})
            }
        )
        queue_url2 = resp['QueueUrl']

        sqs.send_message(QueueUrl=queue_url2, MessageBody='msg1')
        sqs.send_message(QueueUrl=queue_url2, MessageBody='msg2')

    with freeze_time("2015-01-01 13:00:00"):
        resp = sqs.receive_message(QueueUrl=queue_url2, VisibilityTimeout=30, WaitTimeSeconds=0)
        resp['Messages'][0]['Body'].should.equal('msg1')

    with freeze_time("2015-01-01 13:01:00"):
        resp = sqs.receive_message(QueueUrl=queue_url2, VisibilityTimeout=30, WaitTimeSeconds=0)
        resp['Messages'][0]['Body'].should.equal('msg1')

    with freeze_time("2015-01-01 13:02:00"):
        resp = sqs.receive_message(QueueUrl=queue_url2, VisibilityTimeout=30, WaitTimeSeconds=0)
        len(resp['Messages']).should.equal(1)

    resp = sqs.receive_message(QueueUrl=queue_url1, VisibilityTimeout=30, WaitTimeSeconds=0)
    resp['Messages'][0]['Body'].should.equal('msg1')

    # Might as well test list source queues

    resp = sqs.list_dead_letter_source_queues(QueueUrl=queue_url1)
    resp['queueUrls'][0].should.equal(queue_url2)


@mock_sqs
def test_redrive_policy_available():
    sqs = boto3.client('sqs', region_name='us-east-1')

    resp = sqs.create_queue(QueueName='test-deadletter')
    queue_url1 = resp['QueueUrl']
    queue_arn1 = sqs.get_queue_attributes(QueueUrl=queue_url1)['Attributes']['QueueArn']
    redrive_policy = {
        'deadLetterTargetArn': queue_arn1,
        'maxReceiveCount': 1,
    }

    resp = sqs.create_queue(
        QueueName='test-queue',
        Attributes={
            'RedrivePolicy': json.dumps(redrive_policy)
        }
    )

    queue_url2 = resp['QueueUrl']
    attributes = sqs.get_queue_attributes(QueueUrl=queue_url2)['Attributes']
    assert 'RedrivePolicy' in attributes
    assert json.loads(attributes['RedrivePolicy']) == redrive_policy

    # Cant have redrive policy without maxReceiveCount
    with assert_raises(ClientError):
        sqs.create_queue(
            QueueName='test-queue2',
            Attributes={
                'FifoQueue': 'true',
                'RedrivePolicy': json.dumps({'deadLetterTargetArn': queue_arn1})
            }
        )


@mock_sqs
def test_redrive_policy_non_existent_queue():
    sqs = boto3.client('sqs', region_name='us-east-1')
    redrive_policy = {
        'deadLetterTargetArn': 'arn:aws:sqs:us-east-1:123456789012:no-queue',
        'maxReceiveCount': 1,
    }

    with assert_raises(ClientError):
        sqs.create_queue(
            QueueName='test-queue',
            Attributes={
                'RedrivePolicy': json.dumps(redrive_policy)
            }
        )


@mock_sqs
def test_redrive_policy_set_attributes():
    sqs = boto3.resource('sqs', region_name='us-east-1')

    queue = sqs.create_queue(QueueName='test-queue')
    deadletter_queue = sqs.create_queue(QueueName='test-deadletter')

    redrive_policy = {
        'deadLetterTargetArn': deadletter_queue.attributes['QueueArn'],
        'maxReceiveCount': 1,
    }

    queue.set_attributes(Attributes={
        'RedrivePolicy': json.dumps(redrive_policy)})

    copy = sqs.get_queue_by_name(QueueName='test-queue')
    assert 'RedrivePolicy' in copy.attributes
    copy_policy = json.loads(copy.attributes['RedrivePolicy'])
    assert copy_policy == redrive_policy


@mock_sqs
def test_receive_messages_with_message_group_id():
    sqs = boto3.resource('sqs', region_name='us-east-1')
    queue = sqs.create_queue(QueueName="test-queue.fifo",
                             Attributes={
                                 'FifoQueue': 'true',
                             })
    queue.set_attributes(Attributes={"VisibilityTimeout": "3600"})
    queue.send_message(
        MessageBody="message-1",
        MessageGroupId="group"
    )
    queue.send_message(
        MessageBody="message-2",
        MessageGroupId="group"
    )

    messages = queue.receive_messages()
    messages.should.have.length_of(1)
    message = messages[0]

    # received message is not deleted!

    messages = queue.receive_messages(WaitTimeSeconds=0)
    messages.should.have.length_of(0)

    # message is now processed, next one should be available
    message.delete()
    messages = queue.receive_messages()
    messages.should.have.length_of(1)


@mock_sqs
def test_receive_messages_with_message_group_id_on_requeue():
    sqs = boto3.resource('sqs', region_name='us-east-1')
    queue = sqs.create_queue(QueueName="test-queue.fifo",
                             Attributes={
                                 'FifoQueue': 'true',
                             })
    queue.set_attributes(Attributes={"VisibilityTimeout": "3600"})
    queue.send_message(
        MessageBody="message-1",
        MessageGroupId="group"
    )
    queue.send_message(
        MessageBody="message-2",
        MessageGroupId="group"
    )

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
    if os.environ.get('TEST_SERVER_MODE', 'false').lower() == 'true':
        raise SkipTest('Cant manipulate time in server mode')

    with freeze_time("2015-01-01 12:00:00"):
        sqs = boto3.resource('sqs', region_name='us-east-1')
        queue = sqs.create_queue(QueueName="test-queue.fifo",
                                 Attributes={
                                     'FifoQueue': 'true',
                                 })
        queue.set_attributes(Attributes={"VisibilityTimeout": "3600"})
        queue.send_message(
            MessageBody="message-1",
            MessageGroupId="group"
        )
        queue.send_message(
            MessageBody="message-2",
            MessageGroupId="group"
        )

        messages = queue.receive_messages()
        messages.should.have.length_of(1)
        message = messages[0]

        # received message is not deleted!

        messages = queue.receive_messages(WaitTimeSeconds=0)
        messages.should.have.length_of(0)

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
    sqs = boto3.resource('sqs', region_name='us-east-1')

    queue = sqs.create_queue(
        QueueName='test-queue',
        Attributes={
            'ReceiveMessageWaitTimeSeconds': '2',
        }
    )

    queue.receive_messages()
