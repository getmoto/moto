from __future__ import unicode_literals
import boto
import sure  # noqa

from moto import mock_ec2


@mock_ec2
def test_network_acls():

    conn = boto.connect_vpc('the_key', 'the secret')
    vpc = conn.create_vpc("10.0.0.0/16")

    network_acl = conn.create_network_acl(vpc.id)

    all_network_acls = conn.get_all_network_acls()
    all_network_acls.should.have.length_of(1)


@mock_ec2
def test_network_acl_entries():

    conn = boto.connect_vpc('the_key', 'the secret')
    vpc = conn.create_vpc("10.0.0.0/16")

    network_acl = conn.create_network_acl(vpc.id)

    network_acl_entry = conn.create_network_acl_entry(
        network_acl.id, 110, 6,
        'ALLOW', '0.0.0.0/0', False,
        port_range_from='443',
        port_range_to='443'
    )

    all_network_acls = conn.get_all_network_acls()
    all_network_acls.should.have.length_of(1)

    entries = all_network_acls[0].network_acl_entries
    entries.should.have.length_of(1)
    entries[0].rule_number.should.equal('110')
    entries[0].protocol.should.equal('6')
    entries[0].rule_action.should.equal('ALLOW')


