from __future__ import unicode_literals
# Ensure 'assert_raises' context manager support for Python 2.6
import tests.backport_assert_raises
from nose.tools import assert_raises

import boto
import boto3
from boto.exception import EC2ResponseError
import sure  # noqa

from moto import mock_ec2_deprecated, mock_ec2


@mock_ec2_deprecated
def test_console_output():
    conn = boto.connect_ec2('the_key', 'the_secret')
    reservation = conn.run_instances('ami-1234abcd')
    instance_id = reservation.instances[0].id
    output = conn.get_console_output(instance_id)
    output.output.should_not.equal(None)


@mock_ec2_deprecated
def test_console_output_without_instance():
    conn = boto.connect_ec2('the_key', 'the_secret')

    with assert_raises(EC2ResponseError) as cm:
        conn.get_console_output('i-1234abcd')
    cm.exception.code.should.equal('InvalidInstanceID.NotFound')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@mock_ec2
def test_console_output_boto3():
    conn = boto3.resource('ec2', 'us-east-1')
    instances = conn.create_instances(ImageId='ami-1234abcd',
                                      MinCount=1,
                                      MaxCount=1)

    output = instances[0].console_output()
    output.get('Output').should_not.equal(None)
