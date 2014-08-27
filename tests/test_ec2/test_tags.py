from __future__ import unicode_literals
import itertools

import boto
import sure  # noqa

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


@mock_ec2
def test_instance_launch_and_retrieve_all_instances():
    conn = boto.connect_ec2('the_key', 'the_secret')
    reservation = conn.run_instances('ami-1234abcd')
    instance = reservation.instances[0]

    instance.add_tag("a key", "some value")
    chain = itertools.chain.from_iterable
    existing_instances = list(chain([res.instances for res in conn.get_all_instances()]))
    existing_instances.should.have.length_of(1)
    existing_instance = existing_instances[0]
    existing_instance.tags["a key"].should.equal("some value")
