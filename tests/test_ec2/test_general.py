import boto
from boto.exception import EC2ResponseError
import sure  # noqa

from moto import mock_ec2


@mock_ec2
def test_console_output():
    conn = boto.connect_ec2('the_key', 'the_secret')
    reservation = conn.run_instances('ami-1234abcd')
    instance_id = reservation.instances[0].id

    output = conn.get_console_output(instance_id)
    output.output.should_not.equal(None)


@mock_ec2
def test_console_output_without_instance():
    conn = boto.connect_ec2('the_key', 'the_secret')
    conn.get_console_output.when.called_with('i-1234abcd').should.throw(Exception)
