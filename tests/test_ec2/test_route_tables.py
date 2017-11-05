from __future__ import unicode_literals
# Ensure 'assert_raises' context manager support for Python 2.6
import tests.backport_assert_raises
from nose.tools import assert_raises

import boto
import boto3
from boto.exception import EC2ResponseError
import sure  # noqa

from moto import mock_ec2, mock_ec2_deprecated
from tests.helpers import requires_boto_gte


@mock_ec2_deprecated
def test_route_tables_defaults():
    conn = boto.connect_vpc('the_key', 'the_secret')
    vpc = conn.create_vpc("10.0.0.0/16")

    all_route_tables = conn.get_all_route_tables(filters={'vpc-id': vpc.id})
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

    all_route_tables = conn.get_all_route_tables(filters={'vpc-id': vpc.id})
    all_route_tables.should.have.length_of(0)


@mock_ec2_deprecated
def test_route_tables_additional():
    conn = boto.connect_vpc('the_key', 'the_secret')
    vpc = conn.create_vpc("10.0.0.0/16")
    route_table = conn.create_route_table(vpc.id)

    all_route_tables = conn.get_all_route_tables(filters={'vpc-id': vpc.id})
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

    all_route_tables = conn.get_all_route_tables(filters={'vpc-id': vpc.id})
    all_route_tables.should.have.length_of(1)

    with assert_raises(EC2ResponseError) as cm:
        conn.delete_route_table("rtb-1234abcd")
    cm.exception.code.should.equal('InvalidRouteTableID.NotFound')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@mock_ec2_deprecated
def test_route_tables_filters_standard():
    conn = boto.connect_vpc('the_key', 'the_secret')

    vpc1 = conn.create_vpc("10.0.0.0/16")
    route_table1 = conn.create_route_table(vpc1.id)

    vpc2 = conn.create_vpc("10.0.0.0/16")
    route_table2 = conn.create_route_table(vpc2.id)

    all_route_tables = conn.get_all_route_tables()
    all_route_tables.should.have.length_of(5)

    # Filter by main route table
    main_route_tables = conn.get_all_route_tables(
        filters={'association.main': 'true'})
    main_route_tables.should.have.length_of(3)
    main_route_table_ids = [
        route_table.id for route_table in main_route_tables]
    main_route_table_ids.should_not.contain(route_table1.id)
    main_route_table_ids.should_not.contain(route_table2.id)

    # Filter by VPC
    vpc1_route_tables = conn.get_all_route_tables(filters={'vpc-id': vpc1.id})
    vpc1_route_tables.should.have.length_of(2)
    vpc1_route_table_ids = [
        route_table.id for route_table in vpc1_route_tables]
    vpc1_route_table_ids.should.contain(route_table1.id)
    vpc1_route_table_ids.should_not.contain(route_table2.id)

    # Filter by VPC and main route table
    vpc2_main_route_tables = conn.get_all_route_tables(
        filters={'association.main': 'true', 'vpc-id': vpc2.id})
    vpc2_main_route_tables.should.have.length_of(1)
    vpc2_main_route_table_ids = [
        route_table.id for route_table in vpc2_main_route_tables]
    vpc2_main_route_table_ids.should_not.contain(route_table1.id)
    vpc2_main_route_table_ids.should_not.contain(route_table2.id)

    # Unsupported filter
    conn.get_all_route_tables.when.called_with(
        filters={'not-implemented-filter': 'foobar'}).should.throw(NotImplementedError)


@mock_ec2_deprecated
def test_route_tables_filters_associations():
    conn = boto.connect_vpc('the_key', 'the_secret')

    vpc = conn.create_vpc("10.0.0.0/16")
    subnet1 = conn.create_subnet(vpc.id, "10.0.0.0/24")
    subnet2 = conn.create_subnet(vpc.id, "10.0.1.0/24")
    subnet3 = conn.create_subnet(vpc.id, "10.0.2.0/24")
    route_table1 = conn.create_route_table(vpc.id)
    route_table2 = conn.create_route_table(vpc.id)

    association_id1 = conn.associate_route_table(route_table1.id, subnet1.id)
    association_id2 = conn.associate_route_table(route_table1.id, subnet2.id)
    association_id3 = conn.associate_route_table(route_table2.id, subnet3.id)

    all_route_tables = conn.get_all_route_tables()
    all_route_tables.should.have.length_of(4)

    # Filter by association ID
    association1_route_tables = conn.get_all_route_tables(
        filters={'association.route-table-association-id': association_id1})
    association1_route_tables.should.have.length_of(1)
    association1_route_tables[0].id.should.equal(route_table1.id)
    association1_route_tables[0].associations.should.have.length_of(2)

    # Filter by route table ID
    route_table2_route_tables = conn.get_all_route_tables(
        filters={'association.route-table-id': route_table2.id})
    route_table2_route_tables.should.have.length_of(1)
    route_table2_route_tables[0].id.should.equal(route_table2.id)
    route_table2_route_tables[0].associations.should.have.length_of(1)

    # Filter by subnet ID
    subnet_route_tables = conn.get_all_route_tables(
        filters={'association.subnet-id': subnet1.id})
    subnet_route_tables.should.have.length_of(1)
    subnet_route_tables[0].id.should.equal(route_table1.id)
    association1_route_tables[0].associations.should.have.length_of(2)


@mock_ec2_deprecated
def test_route_table_associations():
    conn = boto.connect_vpc('the_key', 'the_secret')
    vpc = conn.create_vpc("10.0.0.0/16")
    subnet = conn.create_subnet(vpc.id, "10.0.0.0/18")
    route_table = conn.create_route_table(vpc.id)

    all_route_tables = conn.get_all_route_tables()
    all_route_tables.should.have.length_of(3)

    # Refresh
    route_table = conn.get_all_route_tables(route_table.id)[0]
    route_table.associations.should.have.length_of(0)

    # Associate
    association_id = conn.associate_route_table(route_table.id, subnet.id)

    # Refresh
    route_table = conn.get_all_route_tables(route_table.id)[0]
    route_table.associations.should.have.length_of(1)

    route_table.associations[0].id.should.equal(association_id)
    route_table.associations[0].main.should.equal(False)
    route_table.associations[0].route_table_id.should.equal(route_table.id)
    route_table.associations[0].subnet_id.should.equal(subnet.id)

    # Associate is idempotent
    association_id_idempotent = conn.associate_route_table(
        route_table.id, subnet.id)
    association_id_idempotent.should.equal(association_id)

    # Error: Attempt delete associated route table.
    with assert_raises(EC2ResponseError) as cm:
        conn.delete_route_table(route_table.id)
    cm.exception.code.should.equal('DependencyViolation')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none

    # Disassociate
    conn.disassociate_route_table(association_id)

    # Refresh
    route_table = conn.get_all_route_tables(route_table.id)[0]
    route_table.associations.should.have.length_of(0)

    # Error: Disassociate with invalid association ID
    with assert_raises(EC2ResponseError) as cm:
        conn.disassociate_route_table(association_id)
    cm.exception.code.should.equal('InvalidAssociationID.NotFound')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none

    # Error: Associate with invalid subnet ID
    with assert_raises(EC2ResponseError) as cm:
        conn.associate_route_table(route_table.id, "subnet-1234abcd")
    cm.exception.code.should.equal('InvalidSubnetID.NotFound')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none

    # Error: Associate with invalid route table ID
    with assert_raises(EC2ResponseError) as cm:
        conn.associate_route_table("rtb-1234abcd", subnet.id)
    cm.exception.code.should.equal('InvalidRouteTableID.NotFound')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@requires_boto_gte("2.16.0")
@mock_ec2_deprecated
def test_route_table_replace_route_table_association():
    """
      Note: Boto has deprecated replace_route_table_assocation (which returns status)
        and now uses replace_route_table_assocation_with_assoc (which returns association ID).
    """
    conn = boto.connect_vpc('the_key', 'the_secret')
    vpc = conn.create_vpc("10.0.0.0/16")
    subnet = conn.create_subnet(vpc.id, "10.0.0.0/18")
    route_table1 = conn.create_route_table(vpc.id)
    route_table2 = conn.create_route_table(vpc.id)

    all_route_tables = conn.get_all_route_tables()
    all_route_tables.should.have.length_of(4)

    # Refresh
    route_table1 = conn.get_all_route_tables(route_table1.id)[0]
    route_table1.associations.should.have.length_of(0)

    # Associate
    association_id1 = conn.associate_route_table(route_table1.id, subnet.id)

    # Refresh
    route_table1 = conn.get_all_route_tables(route_table1.id)[0]
    route_table2 = conn.get_all_route_tables(route_table2.id)[0]

    # Validate
    route_table1.associations.should.have.length_of(1)
    route_table2.associations.should.have.length_of(0)

    route_table1.associations[0].id.should.equal(association_id1)
    route_table1.associations[0].main.should.equal(False)
    route_table1.associations[0].route_table_id.should.equal(route_table1.id)
    route_table1.associations[0].subnet_id.should.equal(subnet.id)

    # Replace Association
    association_id2 = conn.replace_route_table_association_with_assoc(
        association_id1, route_table2.id)

    # Refresh
    route_table1 = conn.get_all_route_tables(route_table1.id)[0]
    route_table2 = conn.get_all_route_tables(route_table2.id)[0]

    # Validate
    route_table1.associations.should.have.length_of(0)
    route_table2.associations.should.have.length_of(1)

    route_table2.associations[0].id.should.equal(association_id2)
    route_table2.associations[0].main.should.equal(False)
    route_table2.associations[0].route_table_id.should.equal(route_table2.id)
    route_table2.associations[0].subnet_id.should.equal(subnet.id)

    # Replace Association is idempotent
    association_id_idempotent = conn.replace_route_table_association_with_assoc(
        association_id2, route_table2.id)
    association_id_idempotent.should.equal(association_id2)

    # Error: Replace association with invalid association ID
    with assert_raises(EC2ResponseError) as cm:
        conn.replace_route_table_association_with_assoc(
            "rtbassoc-1234abcd", route_table1.id)
    cm.exception.code.should.equal('InvalidAssociationID.NotFound')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none

    # Error: Replace association with invalid route table ID
    with assert_raises(EC2ResponseError) as cm:
        conn.replace_route_table_association_with_assoc(
            association_id2, "rtb-1234abcd")
    cm.exception.code.should.equal('InvalidRouteTableID.NotFound')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@mock_ec2_deprecated
def test_route_table_get_by_tag():
    conn = boto.connect_vpc('the_key', 'the_secret')

    vpc = conn.create_vpc('10.0.0.0/16')

    route_table = conn.create_route_table(vpc.id)
    route_table.add_tag('Name', 'TestRouteTable')

    route_tables = conn.get_all_route_tables(
        filters={'tag:Name': 'TestRouteTable'})

    route_tables.should.have.length_of(1)
    route_tables[0].vpc_id.should.equal(vpc.id)
    route_tables[0].id.should.equal(route_table.id)
    route_tables[0].tags.should.have.length_of(1)
    route_tables[0].tags['Name'].should.equal('TestRouteTable')


@mock_ec2
def test_route_table_get_by_tag_boto3():
    ec2 = boto3.resource('ec2', region_name='eu-central-1')

    vpc = ec2.create_vpc(CidrBlock='10.0.0.0/16')

    route_table = ec2.create_route_table(VpcId=vpc.id)
    route_table.create_tags(Tags=[{'Key': 'Name', 'Value': 'TestRouteTable'}])

    filters = [{'Name': 'tag:Name', 'Values': ['TestRouteTable']}]
    route_tables = list(ec2.route_tables.filter(Filters=filters))

    route_tables.should.have.length_of(1)
    route_tables[0].vpc_id.should.equal(vpc.id)
    route_tables[0].id.should.equal(route_table.id)
    route_tables[0].tags.should.have.length_of(1)
    route_tables[0].tags[0].should.equal(
        {'Key': 'Name', 'Value': 'TestRouteTable'})


@mock_ec2_deprecated
def test_routes_additional():
    conn = boto.connect_vpc('the_key', 'the_secret')
    vpc = conn.create_vpc("10.0.0.0/16")
    main_route_table = conn.get_all_route_tables(filters={'vpc-id': vpc.id})[0]
    local_route = main_route_table.routes[0]
    igw = conn.create_internet_gateway()
    ROUTE_CIDR = "10.0.0.4/24"

    conn.create_route(main_route_table.id, ROUTE_CIDR, gateway_id=igw.id)

    main_route_table = conn.get_all_route_tables(
        filters={'vpc-id': vpc.id})[0]  # Refresh route table

    main_route_table.routes.should.have.length_of(2)
    new_routes = [
        route for route in main_route_table.routes if route.destination_cidr_block != vpc.cidr_block]
    new_routes.should.have.length_of(1)

    new_route = new_routes[0]
    new_route.gateway_id.should.equal(igw.id)
    new_route.instance_id.should.be.none
    new_route.state.should.equal('active')
    new_route.destination_cidr_block.should.equal(ROUTE_CIDR)

    conn.delete_route(main_route_table.id, ROUTE_CIDR)

    main_route_table = conn.get_all_route_tables(
        filters={'vpc-id': vpc.id})[0]  # Refresh route table

    main_route_table.routes.should.have.length_of(1)
    new_routes = [
        route for route in main_route_table.routes if route.destination_cidr_block != vpc.cidr_block]
    new_routes.should.have.length_of(0)

    with assert_raises(EC2ResponseError) as cm:
        conn.delete_route(main_route_table.id, ROUTE_CIDR)
    cm.exception.code.should.equal('InvalidRoute.NotFound')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@mock_ec2_deprecated
def test_routes_replace():
    conn = boto.connect_vpc('the_key', 'the_secret')
    vpc = conn.create_vpc("10.0.0.0/16")
    main_route_table = conn.get_all_route_tables(
        filters={'association.main': 'true', 'vpc-id': vpc.id})[0]
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
        routes = [
            route for route in route_table.routes if route.destination_cidr_block != vpc.cidr_block]
        routes.should.have.length_of(1)
        return routes[0]

    conn.replace_route(main_route_table.id, ROUTE_CIDR,
                       instance_id=instance.id)

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
@mock_ec2_deprecated
def test_routes_not_supported():
    conn = boto.connect_vpc('the_key', 'the_secret')
    vpc = conn.create_vpc("10.0.0.0/16")
    main_route_table = conn.get_all_route_tables()[0]
    local_route = main_route_table.routes[0]
    igw = conn.create_internet_gateway()
    ROUTE_CIDR = "10.0.0.4/24"

    # Create
    conn.create_route.when.called_with(
        main_route_table.id, ROUTE_CIDR, interface_id='eni-1234abcd').should.throw(NotImplementedError)

    # Replace
    igw = conn.create_internet_gateway()
    conn.create_route(main_route_table.id, ROUTE_CIDR, gateway_id=igw.id)
    conn.replace_route.when.called_with(
        main_route_table.id, ROUTE_CIDR, interface_id='eni-1234abcd').should.throw(NotImplementedError)


@requires_boto_gte("2.34.0")
@mock_ec2_deprecated
def test_routes_vpc_peering_connection():
    conn = boto.connect_vpc('the_key', 'the_secret')
    vpc = conn.create_vpc("10.0.0.0/16")
    main_route_table = conn.get_all_route_tables(
        filters={'association.main': 'true', 'vpc-id': vpc.id})[0]
    local_route = main_route_table.routes[0]
    ROUTE_CIDR = "10.0.0.4/24"

    peer_vpc = conn.create_vpc("11.0.0.0/16")
    vpc_pcx = conn.create_vpc_peering_connection(vpc.id, peer_vpc.id)

    conn.create_route(main_route_table.id, ROUTE_CIDR,
                      vpc_peering_connection_id=vpc_pcx.id)

    # Refresh route table
    main_route_table = conn.get_all_route_tables(main_route_table.id)[0]
    new_routes = [
        route for route in main_route_table.routes if route.destination_cidr_block != vpc.cidr_block]
    new_routes.should.have.length_of(1)

    new_route = new_routes[0]
    new_route.gateway_id.should.be.none
    new_route.instance_id.should.be.none
    new_route.vpc_peering_connection_id.should.equal(vpc_pcx.id)
    new_route.state.should.equal('blackhole')
    new_route.destination_cidr_block.should.equal(ROUTE_CIDR)


@requires_boto_gte("2.34.0")
@mock_ec2_deprecated
def test_routes_vpn_gateway():

    conn = boto.connect_vpc('the_key', 'the_secret')
    vpc = conn.create_vpc("10.0.0.0/16")
    main_route_table = conn.get_all_route_tables(
        filters={'association.main': 'true', 'vpc-id': vpc.id})[0]
    ROUTE_CIDR = "10.0.0.4/24"

    vpn_gw = conn.create_vpn_gateway(type="ipsec.1")

    conn.create_route(main_route_table.id, ROUTE_CIDR, gateway_id=vpn_gw.id)

    main_route_table = conn.get_all_route_tables(main_route_table.id)[0]
    new_routes = [
        route for route in main_route_table.routes if route.destination_cidr_block != vpc.cidr_block]
    new_routes.should.have.length_of(1)

    new_route = new_routes[0]
    new_route.gateway_id.should.equal(vpn_gw.id)
    new_route.instance_id.should.be.none
    new_route.vpc_peering_connection_id.should.be.none


@mock_ec2_deprecated
def test_network_acl_tagging():

    conn = boto.connect_vpc('the_key', 'the secret')
    vpc = conn.create_vpc("10.0.0.0/16")

    route_table = conn.create_route_table(vpc.id)
    route_table.add_tag("a key", "some value")

    tag = conn.get_all_tags()[0]
    tag.name.should.equal("a key")
    tag.value.should.equal("some value")

    all_route_tables = conn.get_all_route_tables()
    test_route_table = next(na for na in all_route_tables
                            if na.id == route_table.id)
    test_route_table.tags.should.have.length_of(1)
    test_route_table.tags["a key"].should.equal("some value")
