# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import boto
import boto3
import botocore.exceptions
from boto.exception import SQSError
from boto.sqs.message import RawMessage, Message

import base64
import requests
import sure  # noqa
import time

from moto import settings, mock_sqs, mock_sqs_deprecated
from tests.helpers import requires_boto_gte
import tests.backport_assert_raises  # noqa
from nose.tools import assert_raises


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
def test_get_inexistent_queue():
    sqs = boto3.resource('sqs', region_name='us-east-1')
    sqs.get_queue_by_name.when.called_with(
        QueueName='nonexisting-queue').should.throw(botocore.exceptions.ClientError)

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
    msg.get('ResponseMetadata', {}).get('RequestId').should.equal(
        '27daac76-34dd-47df-bd01-1f6e873584a0')
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
    msg.get('ResponseMetadata', {}).get('RequestId').should.equal(
        '27daac76-34dd-47df-bd01-1f6e873584a0')
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
    msg.get('ResponseMetadata', {}).get('RequestId').should.equal(
        '27daac76-34dd-47df-bd01-1f6e873584a0')
    msg.get('MessageId').should_not.contain(' \n')

    messages = queue.receive_messages()
    messages.should.have.length_of(1)


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

    queue.send_message(MessageBody="derp")
    messages = conn.receive_message(
        QueueUrl=queue.url, MaxNumberOfMessages=1)['Messages']

    message = messages[0]
    sent_timestamp = message.get('Attributes').get('SentTimestamp')
    approximate_first_receive_timestamp = message.get('Attributes').get('ApproximateFirstReceiveTimestamp')

    int.when.called_with(sent_timestamp).shouldnt.throw(ValueError)
    int.when.called_with(approximate_first_receive_timestamp).shouldnt.throw(ValueError)


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


@mock_sqs
def test_receive_messages_with_wait_seconds_timeout_of_negative_one():
    """
    test that zero messages is returned with a wait_seconds_timeout of negative 1
    :return:
    """

    sqs = boto3.resource('sqs', region_name='us-east-1')
    queue = sqs.create_queue(QueueName="blah")

    messages = queue.receive_messages(WaitTimeSeconds=-1)
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
