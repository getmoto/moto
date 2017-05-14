from __future__ import unicode_literals
import boto
import sure  # noqa

from moto import mock_ec2_deprecated


@mock_ec2_deprecated
def test_default_network_acl_created_with_vpc():
    conn = boto.connect_vpc('the_key', 'the secret')
    vpc = conn.create_vpc("10.0.0.0/16")
    all_network_acls = conn.get_all_network_acls()
    all_network_acls.should.have.length_of(2)


@mock_ec2_deprecated
def test_network_acls():
    conn = boto.connect_vpc('the_key', 'the secret')
    vpc = conn.create_vpc("10.0.0.0/16")
    network_acl = conn.create_network_acl(vpc.id)
    all_network_acls = conn.get_all_network_acls()
    all_network_acls.should.have.length_of(3)


@mock_ec2_deprecated
def test_new_subnet_associates_with_default_network_acl():
    conn = boto.connect_vpc('the_key', 'the secret')
    vpc = conn.get_all_vpcs()[0]

    subnet = conn.create_subnet(vpc.id, "10.0.0.0/18")
    all_network_acls = conn.get_all_network_acls()
    all_network_acls.should.have.length_of(1)

    acl = all_network_acls[0]
    acl.associations.should.have.length_of(4)
    [a.subnet_id for a in acl.associations].should.contain(subnet.id)


@mock_ec2_deprecated
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
    all_network_acls.should.have.length_of(3)

    test_network_acl = next(na for na in all_network_acls
                            if na.id == network_acl.id)
    entries = test_network_acl.network_acl_entries
    entries.should.have.length_of(1)
    entries[0].rule_number.should.equal('110')
    entries[0].protocol.should.equal('6')
    entries[0].rule_action.should.equal('ALLOW')


@mock_ec2_deprecated
def test_delete_network_acl_entry():
    conn = boto.connect_vpc('the_key', 'the secret')
    vpc = conn.create_vpc("10.0.0.0/16")

    network_acl = conn.create_network_acl(vpc.id)

    conn.create_network_acl_entry(
        network_acl.id, 110, 6,
        'ALLOW', '0.0.0.0/0', False,
        port_range_from='443',
        port_range_to='443'
    )
    conn.delete_network_acl_entry(
        network_acl.id, 110, False
    )

    all_network_acls = conn.get_all_network_acls()

    test_network_acl = next(na for na in all_network_acls
                            if na.id == network_acl.id)
    entries = test_network_acl.network_acl_entries
    entries.should.have.length_of(0)


@mock_ec2_deprecated
def test_replace_network_acl_entry():
    conn = boto.connect_vpc('the_key', 'the secret')
    vpc = conn.create_vpc("10.0.0.0/16")

    network_acl = conn.create_network_acl(vpc.id)

    conn.create_network_acl_entry(
        network_acl.id, 110, 6,
        'ALLOW', '0.0.0.0/0', False,
        port_range_from='443',
        port_range_to='443'
    )
    conn.replace_network_acl_entry(
        network_acl.id, 110, -1,
        'DENY', '0.0.0.0/0', False,
        port_range_from='22',
        port_range_to='22'
    )

    all_network_acls = conn.get_all_network_acls()

    test_network_acl = next(na for na in all_network_acls
                            if na.id == network_acl.id)
    entries = test_network_acl.network_acl_entries
    entries.should.have.length_of(1)
    entries[0].rule_number.should.equal('110')
    entries[0].protocol.should.equal('-1')
    entries[0].rule_action.should.equal('DENY')

@mock_ec2_deprecated
def test_associate_new_network_acl_with_subnet():
    conn = boto.connect_vpc('the_key', 'the secret')
    vpc = conn.create_vpc("10.0.0.0/16")
    subnet = conn.create_subnet(vpc.id, "10.0.0.0/18")
    network_acl = conn.create_network_acl(vpc.id)

    conn.associate_network_acl(network_acl.id, subnet.id)

    all_network_acls = conn.get_all_network_acls()
    all_network_acls.should.have.length_of(3)

    test_network_acl = next(na for na in all_network_acls
                            if na.id == network_acl.id)

    test_network_acl.associations.should.have.length_of(1)
    test_network_acl.associations[0].subnet_id.should.equal(subnet.id)


@mock_ec2_deprecated
def test_delete_network_acl():
    conn = boto.connect_vpc('the_key', 'the secret')
    vpc = conn.create_vpc("10.0.0.0/16")
    subnet = conn.create_subnet(vpc.id, "10.0.0.0/18")
    network_acl = conn.create_network_acl(vpc.id)

    all_network_acls = conn.get_all_network_acls()
    all_network_acls.should.have.length_of(3)

    any(acl.id == network_acl.id for acl in all_network_acls).should.be.ok

    conn.delete_network_acl(network_acl.id)

    updated_network_acls = conn.get_all_network_acls()
    updated_network_acls.should.have.length_of(2)

    any(acl.id == network_acl.id for acl in updated_network_acls).shouldnt.be.ok


@mock_ec2_deprecated
def test_network_acl_tagging():
    conn = boto.connect_vpc('the_key', 'the secret')
    vpc = conn.create_vpc("10.0.0.0/16")
    network_acl = conn.create_network_acl(vpc.id)

    network_acl.add_tag("a key", "some value")

    tag = conn.get_all_tags()[0]
    tag.name.should.equal("a key")
    tag.value.should.equal("some value")

    all_network_acls = conn.get_all_network_acls()
    test_network_acl = next(na for na in all_network_acls
                            if na.id == network_acl.id)
    test_network_acl.tags.should.have.length_of(1)
    test_network_acl.tags["a key"].should.equal("some value")
