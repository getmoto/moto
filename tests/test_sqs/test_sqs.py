import boto
from boto.exception import SQSError
from boto.sqs.message import RawMessage
import requests
import sure  # noqa

from moto import mock_sqs


@mock_sqs
def test_create_queue():
    conn = boto.connect_sqs('the_key', 'the_secret')
    conn.create_queue("test-queue", visibility_timeout=60)

    all_queues = conn.get_all_queues()
    all_queues[0].name.should.equal("test-queue")

    all_queues[0].get_timeout().should.equal(60)


@mock_sqs
def test_get_queue():
    conn = boto.connect_sqs('the_key', 'the_secret')
    conn.create_queue("test-queue", visibility_timeout=60)

    queue = conn.get_queue("test-queue")
    queue.name.should.equal("test-queue")
    queue.get_timeout().should.equal(60)

    nonexisting_queue = conn.get_queue("nonexisting_queue")
    nonexisting_queue.should.be.none


@mock_sqs
def test_delete_queue():
    conn = boto.connect_sqs('the_key', 'the_secret')
    queue = conn.create_queue("test-queue", visibility_timeout=60)

    conn.get_all_queues().should.have.length_of(1)

    queue.delete()
    conn.get_all_queues().should.have.length_of(0)

    queue.delete.when.called_with().should.throw(SQSError)


@mock_sqs
def test_set_queue_attribute():
    conn = boto.connect_sqs('the_key', 'the_secret')
    conn.create_queue("test-queue", visibility_timeout=60)

    queue = conn.get_all_queues()[0]
    queue.get_timeout().should.equal(60)

    queue.set_attribute("VisibilityTimeout", 45)
    queue = conn.get_all_queues()[0]
    queue.get_timeout().should.equal(45)


@mock_sqs
def test_send_message():
    conn = boto.connect_sqs('the_key', 'the_secret')
    queue = conn.create_queue("test-queue", visibility_timeout=60)

    conn.send_message(queue, 'this is a test message')
    conn.send_message(queue, 'this is another test message')

    messages = conn.receive_message(queue, number_messages=1)
    messages[0].get_body().should.equal('this is a test message')


@mock_sqs
def test_read_message_from_queue():
    conn = boto.connect_sqs()
    queue = conn.create_queue('testqueue')
    queue.write(queue.new_message('foo bar baz'))
    message = queue.read(1)
    message.get_body().should.equal('foo bar baz')


@mock_sqs
def test_queue_length():
    conn = boto.connect_sqs('the_key', 'the_secret')
    queue = conn.create_queue("test-queue", visibility_timeout=60)

    conn.send_message(queue, 'this is a test message')
    conn.send_message(queue, 'this is another test message')
    queue.count().should.equal(2)


@mock_sqs
def test_delete_message():
    conn = boto.connect_sqs('the_key', 'the_secret')
    queue = conn.create_queue("test-queue", visibility_timeout=60)

    conn.send_message(queue, 'this is a test message')
    conn.send_message(queue, 'this is another test message')

    messages = conn.receive_message(queue, number_messages=1)
    messages[0].delete()

    queue.count().should.equal(1)


@mock_sqs
def test_send_batch_operation():
    conn = boto.connect_sqs('the_key', 'the_secret')
    queue = conn.create_queue("test-queue", visibility_timeout=60)

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


@mock_sqs
def test_delete_batch_operation():
    conn = boto.connect_sqs('the_key', 'the_secret')
    queue = conn.create_queue("test-queue", visibility_timeout=60)

    conn.send_message_batch(queue, [
        ("my_first_message", 'test message 1', 0),
        ("my_second_message", 'test message 2', 0),
        ("my_third_message", 'test message 3', 0),
    ])

    messages = queue.get_messages(2)
    queue.delete_message_batch(messages)

    queue.count().should.equal(1)


@mock_sqs
def test_sqs_method_not_implemented():
    requests.post.when.called_with("https://sqs.amazonaws.com/?Action=[foobar]").should.throw(NotImplementedError)


@mock_sqs
def test_queue_attributes():
    conn = boto.connect_sqs('the_key', 'the_secret')

    queue_name = 'test-queue'
    visibility_timeout = 60

    queue = conn.create_queue(queue_name, visibility_timeout=visibility_timeout)

    attributes = queue.get_attributes()

    attributes['QueueArn'].should.look_like(
        'arn:aws:sqs:sqs.us-east-1:123456789012:%s' % queue_name)

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
