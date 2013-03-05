import boto
import sure  # flake8: noqa

from moto import mock_ec2


@mock_ec2
def test_instance_launch_and_terminate():
    conn = boto.connect_ec2('the_key', 'the_secret')
    reservation = conn.run_instances('ami-1234abcd')
    instance = reservation.instances[0]

    instance.add_tag("a key", "some value")

    tags = conn.get_all_tags()
    tag = tags[0]
    tag.name.should.equal("a key")
    tag.value.should.equal("some value")

    instance.remove_tag("a key")
    conn.get_all_tags().should.have.length_of(0)
