from __future__ import unicode_literals
# Ensure 'assert_raises' context manager support for Python 2.6
import tests.backport_assert_raises
from nose.tools import assert_raises

import boto
from boto.exception import EC2ResponseError
import sure  # noqa

from moto import mock_ec2
from tests.helpers import requires_boto_gte


@mock_ec2
def test_route_tables_defaults():
    conn = boto.connect_vpc('the_key', 'the_secret')
    vpc = conn.create_vpc("10.0.0.0/16")

    all_route_tables = conn.get_all_route_tables()
    all_route_tables.should.have.length_of(1)

    main_route_table = all_route_tables[0]
    main_route_table.vpc_id.should.equal(vpc.id)

    routes = main_route_table.routes
    routes.should.have.length_of(1)

    local_route = routes[0]
    local_route.gateway_id.should.equal('local')
    local_route.state.should.equal('active')
    local_route.destination_cidr_block.should.equal(vpc.cidr_block)

    vpc.delete()

    all_route_tables = conn.get_all_route_tables()
    all_route_tables.should.have.length_of(0)


@mock_ec2
def test_route_tables_additional():
    conn = boto.connect_vpc('the_key', 'the_secret')
    vpc = conn.create_vpc("10.0.0.0/16")
    route_table = conn.create_route_table(vpc.id)

    all_route_tables = conn.get_all_route_tables()
    all_route_tables.should.have.length_of(2)
    all_route_tables[0].vpc_id.should.equal(vpc.id)
    all_route_tables[1].vpc_id.should.equal(vpc.id)

    all_route_table_ids = [route_table.id for route_table in all_route_tables]
    all_route_table_ids.should.contain(route_table.id)

    routes = route_table.routes
    routes.should.have.length_of(1)

    local_route = routes[0]
    local_route.gateway_id.should.equal('local')
    local_route.state.should.equal('active')
    local_route.destination_cidr_block.should.equal(vpc.cidr_block)

    with assert_raises(EC2ResponseError) as cm:
        conn.delete_vpc(vpc.id)
    cm.exception.code.should.equal('DependencyViolation')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none

    conn.delete_route_table(route_table.id)

    all_route_tables = conn.get_all_route_tables()
    all_route_tables.should.have.length_of(1)

    with assert_raises(EC2ResponseError) as cm:
        conn.delete_route_table("rtb-1234abcd")
    cm.exception.code.should.equal('InvalidRouteTableID.NotFound')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@mock_ec2
def test_route_tables_filters():
    conn = boto.connect_vpc('the_key', 'the_secret')

    vpc1 = conn.create_vpc("10.0.0.0/16")
    route_table1 = conn.create_route_table(vpc1.id)

    vpc2 = conn.create_vpc("10.0.0.0/16")
    route_table2 = conn.create_route_table(vpc2.id)

    all_route_tables = conn.get_all_route_tables()
    all_route_tables.should.have.length_of(4)

    # Filter by main route table
    main_route_tables = conn.get_all_route_tables(filters={'association.main':'true'})
    main_route_tables.should.have.length_of(2)
    main_route_table_ids = [route_table.id for route_table in main_route_tables]
    main_route_table_ids.should_not.contain(route_table1.id)
    main_route_table_ids.should_not.contain(route_table2.id)

    # Filter by VPC
    vpc1_route_tables = conn.get_all_route_tables(filters={'vpc-id':vpc1.id})
    vpc1_route_tables.should.have.length_of(2)
    vpc1_route_table_ids = [route_table.id for route_table in vpc1_route_tables]
    vpc1_route_table_ids.should.contain(route_table1.id)
    vpc1_route_table_ids.should_not.contain(route_table2.id)

    # Filter by VPC and main route table
    vpc2_main_route_tables = conn.get_all_route_tables(filters={'association.main':'true', 'vpc-id':vpc2.id})
    vpc2_main_route_tables.should.have.length_of(1)
    vpc2_main_route_table_ids = [route_table.id for route_table in vpc2_main_route_tables]
    vpc2_main_route_table_ids.should_not.contain(route_table1.id)
    vpc2_main_route_table_ids.should_not.contain(route_table2.id)

    # Unsupported filter
    conn.get_all_route_tables.when.called_with(filters={'not-implemented-filter': 'foobar'}).should.throw(NotImplementedError)


@mock_ec2
def test_routes_additional():
    conn = boto.connect_vpc('the_key', 'the_secret')
    vpc = conn.create_vpc("10.0.0.0/16")
    main_route_table = conn.get_all_route_tables()[0]
    local_route = main_route_table.routes[0]
    igw = conn.create_internet_gateway()
    ROUTE_CIDR = "10.0.0.4/24"

    conn.create_route(main_route_table.id, ROUTE_CIDR, gateway_id=igw.id)

    main_route_table = conn.get_all_route_tables()[0] # Refresh route table

    main_route_table.routes.should.have.length_of(2)
    new_routes = [route for route in main_route_table.routes if route.destination_cidr_block != vpc.cidr_block]
    new_routes.should.have.length_of(1)

    new_route = new_routes[0]
    new_route.gateway_id.should.equal(igw.id)
    new_route.instance_id.should.be.none
    new_route.state.should.equal('active')
    new_route.destination_cidr_block.should.equal(ROUTE_CIDR)

    conn.delete_route(main_route_table.id, ROUTE_CIDR)

    main_route_table = conn.get_all_route_tables()[0] # Refresh route table

    main_route_table.routes.should.have.length_of(1)
    new_routes = [route for route in main_route_table.routes if route.destination_cidr_block != vpc.cidr_block]
    new_routes.should.have.length_of(0)

    with assert_raises(EC2ResponseError) as cm:
        conn.delete_route(main_route_table.id, ROUTE_CIDR)
    cm.exception.code.should.equal('InvalidRoute.NotFound')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@mock_ec2
def test_routes_replace():
    conn = boto.connect_vpc('the_key', 'the_secret')
    vpc = conn.create_vpc("10.0.0.0/16")
    main_route_table = conn.get_all_route_tables(filters={'association.main':'true','vpc-id':vpc.id})[0]
    local_route = main_route_table.routes[0]
    ROUTE_CIDR = "10.0.0.4/24"

    # Various route targets
    igw = conn.create_internet_gateway()

    reservation = conn.run_instances('ami-1234abcd')
    instance = reservation.instances[0]

    # Create initial route
    conn.create_route(main_route_table.id, ROUTE_CIDR, gateway_id=igw.id)

    # Replace...
    def get_target_route():
        route_table = conn.get_all_route_tables(main_route_table.id)[0]
        routes = [route for route in route_table.routes if route.destination_cidr_block != vpc.cidr_block]
        routes.should.have.length_of(1)
        return routes[0]

    conn.replace_route(main_route_table.id, ROUTE_CIDR, instance_id=instance.id)

    target_route = get_target_route()
    target_route.gateway_id.should.be.none
    target_route.instance_id.should.equal(instance.id)
    target_route.state.should.equal('active')
    target_route.destination_cidr_block.should.equal(ROUTE_CIDR)

    conn.replace_route(main_route_table.id, ROUTE_CIDR, gateway_id=igw.id)

    target_route = get_target_route()
    target_route.gateway_id.should.equal(igw.id)
    target_route.instance_id.should.be.none
    target_route.state.should.equal('active')
    target_route.destination_cidr_block.should.equal(ROUTE_CIDR)

    with assert_raises(EC2ResponseError) as cm:
        conn.replace_route('rtb-1234abcd', ROUTE_CIDR, gateway_id=igw.id)
    cm.exception.code.should.equal('InvalidRouteTableID.NotFound')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@requires_boto_gte("2.19.0")
@mock_ec2
def test_routes_not_supported():
    conn = boto.connect_vpc('the_key', 'the_secret')
    vpc = conn.create_vpc("10.0.0.0/16")
    main_route_table = conn.get_all_route_tables()[0]
    local_route = main_route_table.routes[0]
    igw = conn.create_internet_gateway()
    ROUTE_CIDR = "10.0.0.4/24"

    # Create
    conn.create_route.when.called_with(main_route_table.id, ROUTE_CIDR, interface_id='eni-1234abcd').should.throw(NotImplementedError)

    # Replace
    igw = conn.create_internet_gateway()
    conn.create_route(main_route_table.id, ROUTE_CIDR, gateway_id=igw.id)
    conn.replace_route.when.called_with(main_route_table.id, ROUTE_CIDR, interface_id='eni-1234abcd').should.throw(NotImplementedError)


#@requires_boto_gte("2.32.2")
#@mock_ec2
#def test_routes_vpc_peering_connection():
#    conn = boto.connect_vpc('the_key', 'the_secret')
#    vpc = conn.create_vpc("10.0.0.0/16")
#    main_route_table = conn.get_all_route_tables(filters={'association.main':'true','vpc-id':vpc.id})[0]
#    local_route = main_route_table.routes[0]
#    ROUTE_CIDR = "10.0.0.4/24"
#
#    peer_vpc = conn.create_vpc("11.0.0.0/16")
#    vpc_pcx = conn.create_vpc_peering_connection(vpc.id, peer_vpc.id)
#
#    conn.create_route(main_route_table.id, ROUTE_CIDR, vpc_peering_connection_id=vpc_pcx.id)
#
#    # Refresh route table
#    main_route_table = conn.get_all_route_tables(main_route_table.id)[0]
#    new_routes = [route for route in main_route_table.routes if route.destination_cidr_block != vpc.cidr_block]
#    new_routes.should.have.length_of(1)
#
#    new_route = new_routes[0]
#    new_route.gateway_id.should.be.none
#    new_route.instance_id.should.be.none
#    new_route.vpc_peering_connection_id.should.equal(vpc_pcx.id)
#    new_route.state.should.equal('blackhole')
#    new_route.destination_cidr_block.should.equal(ROUTE_CIDR)

