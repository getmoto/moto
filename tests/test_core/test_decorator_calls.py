from __future__ import unicode_literals
import boto
from boto.exception import EC2ResponseError
import sure  # noqa

from moto import mock_ec2

'''
Test the different ways that the decorator can be used
'''


@mock_ec2
def test_basic_connect():
    boto.connect_ec2()


@mock_ec2
def test_basic_decorator():
    conn = boto.connect_ec2('the_key', 'the_secret')
    list(conn.get_all_instances()).should.equal([])


def test_context_manager():
    conn = boto.connect_ec2('the_key', 'the_secret')
    conn.get_all_instances.when.called_with().should.throw(EC2ResponseError)

    with mock_ec2():
        conn = boto.connect_ec2('the_key', 'the_secret')
        list(conn.get_all_instances()).should.equal([])

    conn.get_all_instances.when.called_with().should.throw(EC2ResponseError)


def test_decorator_start_and_stop():
    conn = boto.connect_ec2('the_key', 'the_secret')
    conn.get_all_instances.when.called_with().should.throw(EC2ResponseError)

    mock = mock_ec2()
    mock.start()
    conn = boto.connect_ec2('the_key', 'the_secret')
    list(conn.get_all_instances()).should.equal([])
    mock.stop()

    conn.get_all_instances.when.called_with().should.throw(EC2ResponseError)


@mock_ec2
def test_decorater_wrapped_gets_set():
    """
    Moto decorator's __wrapped__ should get set to the tests function
    """
    test_decorater_wrapped_gets_set.__wrapped__.__name__.should.equal('test_decorater_wrapped_gets_set')
