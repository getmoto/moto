from __future__ import unicode_literals
import boto
from nose.tools import assert_raises
import sure  # noqa
from boto.exception import EC2ResponseError

from moto import mock_ec2_deprecated


@mock_ec2_deprecated
def test_create_vpn_connections():
    conn = boto.connect_vpc('the_key', 'the_secret')
    vpn_connection = conn.create_vpn_connection(
        'ipsec.1', 'vgw-0123abcd', 'cgw-0123abcd')
    vpn_connection.should_not.be.none
    vpn_connection.id.should.match(r'vpn-\w+')
    vpn_connection.type.should.equal('ipsec.1')


@mock_ec2_deprecated
def test_delete_vpn_connections():
    conn = boto.connect_vpc('the_key', 'the_secret')
    vpn_connection = conn.create_vpn_connection(
        'ipsec.1', 'vgw-0123abcd', 'cgw-0123abcd')
    list_of_vpn_connections = conn.get_all_vpn_connections()
    list_of_vpn_connections.should.have.length_of(1)
    conn.delete_vpn_connection(vpn_connection.id)
    list_of_vpn_connections = conn.get_all_vpn_connections()
    list_of_vpn_connections.should.have.length_of(0)


@mock_ec2_deprecated
def test_delete_vpn_connections_bad_id():
    conn = boto.connect_vpc('the_key', 'the_secret')
    with assert_raises(EC2ResponseError):
        conn.delete_vpn_connection('vpn-0123abcd')


@mock_ec2_deprecated
def test_describe_vpn_connections():
    conn = boto.connect_vpc('the_key', 'the_secret')
    list_of_vpn_connections = conn.get_all_vpn_connections()
    list_of_vpn_connections.should.have.length_of(0)
    conn.create_vpn_connection('ipsec.1', 'vgw-0123abcd', 'cgw-0123abcd')
    list_of_vpn_connections = conn.get_all_vpn_connections()
    list_of_vpn_connections.should.have.length_of(1)
    vpn = conn.create_vpn_connection('ipsec.1', 'vgw-1234abcd', 'cgw-1234abcd')
    list_of_vpn_connections = conn.get_all_vpn_connections()
    list_of_vpn_connections.should.have.length_of(2)
    list_of_vpn_connections = conn.get_all_vpn_connections(vpn.id)
    list_of_vpn_connections.should.have.length_of(1)
