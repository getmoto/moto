import boto
from boto.exception import SQSError

from sure import expect

from moto import mock_sqs


@mock_sqs
def test_create_queue():
    conn = boto.connect_sqs('the_key', 'the_secret')
    conn.create_queue("test-queue", visibility_timeout=60)

    all_queues = conn.get_all_queues()
    all_queues[0].name.should.equal("test-queue")

    all_queues[0].get_timeout().should.equal(60)


@mock_sqs
def test_delete_queue():
    conn = boto.connect_sqs('the_key', 'the_secret')
    queue = conn.create_queue("test-queue", visibility_timeout=60)

    conn.get_all_queues().should.have.length_of(1)

    queue.delete()
    conn.get_all_queues().should.have.length_of(0)

    queue.delete.when.called_with().should.throw(SQSError)
