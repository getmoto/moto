import pytest

import boto
import boto3
from boto.exception import EC2ResponseError
from botocore.exceptions import ClientError
import sure  # noqa # pylint: disable=unused-import

from moto import mock_ec2, mock_ec2_deprecated, settings
from tests import EXAMPLE_AMI_ID
from tests.helpers import requires_boto_gte
from uuid import uuid4


# Has boto3 equivalent
@mock_ec2_deprecated
def test_route_tables_defaults():
    conn = boto.connect_vpc("the_key", "the_secret")
    vpc = conn.create_vpc("10.0.0.0/16")

    all_route_tables = conn.get_all_route_tables(filters={"vpc-id": vpc.id})
    all_route_tables.should.have.length_of(1)

    main_route_table = all_route_tables[0]
    main_route_table.vpc_id.should.equal(vpc.id)

    routes = main_route_table.routes
    routes.should.have.length_of(1)

    local_route = routes[0]
    local_route.gateway_id.should.equal("local")
    local_route.state.should.equal("active")
    local_route.destination_cidr_block.should.equal(vpc.cidr_block)

    vpc.delete()

    all_route_tables = conn.get_all_route_tables(filters={"vpc-id": vpc.id})
    all_route_tables.should.have.length_of(0)


@mock_ec2
def test_route_tables_defaults_boto3():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")

    all_route_tables = client.describe_route_tables(
        Filters=[{"Name": "vpc-id", "Values": [vpc.id]}]
    )["RouteTables"]
    all_route_tables.should.have.length_of(1)

    main_route_table = all_route_tables[0]
    main_route_table["VpcId"].should.equal(vpc.id)

    routes = main_route_table["Routes"]
    routes.should.have.length_of(1)

    local_route = routes[0]
    local_route["GatewayId"].should.equal("local")
    local_route["State"].should.equal("active")
    local_route["DestinationCidrBlock"].should.equal(vpc.cidr_block)

    vpc.delete()

    all_route_tables = client.describe_route_tables(
        Filters=[{"Name": "vpc-id", "Values": [vpc.id]}]
    )["RouteTables"]
    all_route_tables.should.have.length_of(0)


# Has boto3 equivalent
@mock_ec2_deprecated
def test_route_tables_additional():
    conn = boto.connect_vpc("the_key", "the_secret")
    vpc = conn.create_vpc("10.0.0.0/16")
    route_table = conn.create_route_table(vpc.id)

    all_route_tables = conn.get_all_route_tables(filters={"vpc-id": vpc.id})
    all_route_tables.should.have.length_of(2)
    all_route_tables[0].vpc_id.should.equal(vpc.id)
    all_route_tables[1].vpc_id.should.equal(vpc.id)

    all_route_table_ids = [route_table.id for route_table in all_route_tables]
    all_route_table_ids.should.contain(route_table.id)

    routes = route_table.routes
    routes.should.have.length_of(1)

    local_route = routes[0]
    local_route.gateway_id.should.equal("local")
    local_route.state.should.equal("active")
    local_route.destination_cidr_block.should.equal(vpc.cidr_block)

    with pytest.raises(EC2ResponseError) as cm:
        conn.delete_vpc(vpc.id)
    cm.value.code.should.equal("DependencyViolation")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none

    conn.delete_route_table(route_table.id)

    all_route_tables = conn.get_all_route_tables(filters={"vpc-id": vpc.id})
    all_route_tables.should.have.length_of(1)

    with pytest.raises(EC2ResponseError) as cm:
        conn.delete_route_table("rtb-1234abcd")
    cm.value.code.should.equal("InvalidRouteTableID.NotFound")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none


@mock_ec2
def test_route_tables_additional_boto3():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    route_table = vpc.create_route_table()

    all_route_tables = client.describe_route_tables(
        Filters=[{"Name": "vpc-id", "Values": [vpc.id]}]
    )["RouteTables"]
    all_route_tables.should.have.length_of(2)
    all_route_tables[0]["VpcId"].should.equal(vpc.id)
    all_route_tables[1]["VpcId"].should.equal(vpc.id)

    all_route_table_ids = [r["RouteTableId"] for r in all_route_tables]
    all_route_table_ids.should.contain(route_table.route_table_id)

    routes = route_table.routes
    routes.should.have.length_of(1)

    local_route = routes[0]
    local_route.gateway_id.should.equal("local")
    local_route.state.should.equal("active")
    local_route.destination_cidr_block.should.equal(vpc.cidr_block)

    with pytest.raises(ClientError) as ex:
        client.delete_vpc(VpcId=vpc.id)
    ex.value.response["Error"]["Code"].should.equal("DependencyViolation")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")

    client.delete_route_table(RouteTableId=route_table.route_table_id)

    all_route_tables = client.describe_route_tables(
        Filters=[{"Name": "vpc-id", "Values": [vpc.id]}]
    )["RouteTables"]
    all_route_tables.should.have.length_of(1)

    with pytest.raises(ClientError) as ex:
        client.delete_route_table(RouteTableId="rtb-1234abcd")
    ex.value.response["Error"]["Code"].should.equal("InvalidRouteTableID.NotFound")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")


# Has boto3 equivalent
@mock_ec2_deprecated
def test_route_tables_filters_standard():
    conn = boto.connect_vpc("the_key", "the_secret")

    vpc1 = conn.create_vpc("10.0.0.0/16")
    route_table1 = conn.create_route_table(vpc1.id)

    vpc2 = conn.create_vpc("10.0.0.0/16")
    route_table2 = conn.create_route_table(vpc2.id)

    all_route_tables = conn.get_all_route_tables()
    all_route_tables.should.have.length_of(5)

    # Filter by main route table
    main_route_tables = conn.get_all_route_tables(filters={"association.main": "true"})
    main_route_tables.should.have.length_of(3)
    main_route_table_ids = [route_table.id for route_table in main_route_tables]
    main_route_table_ids.should_not.contain(route_table1.id)
    main_route_table_ids.should_not.contain(route_table2.id)

    # Filter by VPC
    vpc1_route_tables = conn.get_all_route_tables(filters={"vpc-id": vpc1.id})
    vpc1_route_tables.should.have.length_of(2)
    vpc1_route_table_ids = [route_table.id for route_table in vpc1_route_tables]
    vpc1_route_table_ids.should.contain(route_table1.id)
    vpc1_route_table_ids.should_not.contain(route_table2.id)

    # Filter by VPC and main route table
    vpc2_main_route_tables = conn.get_all_route_tables(
        filters={"association.main": "true", "vpc-id": vpc2.id}
    )
    vpc2_main_route_tables.should.have.length_of(1)
    vpc2_main_route_table_ids = [
        route_table.id for route_table in vpc2_main_route_tables
    ]
    vpc2_main_route_table_ids.should_not.contain(route_table1.id)
    vpc2_main_route_table_ids.should_not.contain(route_table2.id)

    # Unsupported filter
    conn.get_all_route_tables.when.called_with(
        filters={"not-implemented-filter": "foobar"}
    ).should.throw(NotImplementedError)


@mock_ec2
def test_route_tables_filters_standard_boto3():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    vpc1 = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    route_table1 = ec2.create_route_table(VpcId=vpc1.id)

    vpc2 = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    route_table2 = ec2.create_route_table(VpcId=vpc2.id)

    all_route_tables = client.describe_route_tables()["RouteTables"]
    all_ids = [rt["RouteTableId"] for rt in all_route_tables]
    all_ids.should.contain(route_table1.id)
    all_ids.should.contain(route_table2.id)

    # Filter by main route table
    main_route_tables = client.describe_route_tables(
        Filters=[{"Name": "association.main", "Values": ["true"]}]
    )["RouteTables"]
    main_route_table_ids = [
        route_table["RouteTableId"] for route_table in main_route_tables
    ]
    main_route_table_ids.should_not.contain(route_table1.id)
    main_route_table_ids.should_not.contain(route_table2.id)

    # Filter by VPC
    vpc1_route_tables = client.describe_route_tables(
        Filters=[{"Name": "vpc-id", "Values": [vpc1.id]}]
    )["RouteTables"]
    vpc1_route_tables.should.have.length_of(2)
    vpc1_route_table_ids = [
        route_table["RouteTableId"] for route_table in vpc1_route_tables
    ]
    vpc1_route_table_ids.should.contain(route_table1.id)
    vpc1_route_table_ids.should_not.contain(route_table2.id)

    # Filter by VPC and main route table
    vpc2_main_route_tables = client.describe_route_tables(
        Filters=[
            {"Name": "association.main", "Values": ["true"]},
            {"Name": "vpc-id", "Values": [vpc2.id]},
        ]
    )["RouteTables"]
    vpc2_main_route_tables.should.have.length_of(1)
    vpc2_main_route_table_ids = [
        route_table["RouteTableId"] for route_table in vpc2_main_route_tables
    ]
    vpc2_main_route_table_ids.should_not.contain(route_table1.id)
    vpc2_main_route_table_ids.should_not.contain(route_table2.id)

    # Unsupported filter
    if not settings.TEST_SERVER_MODE:
        # ServerMode will just throw a generic 500
        filters = [{"Name": "not-implemented-filter", "Values": ["foobar"]}]
        client.describe_route_tables.when.called_with(Filters=filters).should.throw(
            NotImplementedError
        )


# Has boto3 equivalent
@mock_ec2_deprecated
def test_route_tables_filters_associations():
    conn = boto.connect_vpc("the_key", "the_secret")

    vpc = conn.create_vpc("10.0.0.0/16")
    subnet1 = conn.create_subnet(vpc.id, "10.0.0.0/24")
    subnet2 = conn.create_subnet(vpc.id, "10.0.1.0/24")
    subnet3 = conn.create_subnet(vpc.id, "10.0.2.0/24")
    route_table1 = conn.create_route_table(vpc.id)
    route_table2 = conn.create_route_table(vpc.id)

    association_id1 = conn.associate_route_table(route_table1.id, subnet1.id)
    conn.associate_route_table(route_table1.id, subnet2.id)
    conn.associate_route_table(route_table2.id, subnet3.id)

    all_route_tables = conn.get_all_route_tables()
    all_route_tables.should.have.length_of(4)

    # Filter by association ID
    association1_route_tables = conn.get_all_route_tables(
        filters={"association.route-table-association-id": association_id1}
    )
    association1_route_tables.should.have.length_of(1)
    association1_route_tables[0].id.should.equal(route_table1.id)
    association1_route_tables[0].associations.should.have.length_of(3)

    # Filter by route table ID
    route_table2_route_tables = conn.get_all_route_tables(
        filters={"association.route-table-id": route_table2.id}
    )
    route_table2_route_tables.should.have.length_of(1)
    route_table2_route_tables[0].id.should.equal(route_table2.id)
    route_table2_route_tables[0].associations.should.have.length_of(2)

    # Filter by subnet ID
    subnet_route_tables = conn.get_all_route_tables(
        filters={"association.subnet-id": subnet1.id}
    )
    subnet_route_tables.should.have.length_of(1)
    subnet_route_tables[0].id.should.equal(route_table1.id)
    association1_route_tables[0].associations.should.have.length_of(3)


@mock_ec2
def test_route_tables_filters_associations_boto3():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet1 = vpc.create_subnet(VpcId=vpc.id, CidrBlock="10.0.0.0/24")
    subnet2 = vpc.create_subnet(VpcId=vpc.id, CidrBlock="10.0.1.0/24")
    subnet3 = vpc.create_subnet(VpcId=vpc.id, CidrBlock="10.0.2.0/24")
    route_table1 = ec2.create_route_table(VpcId=vpc.id)
    route_table2 = ec2.create_route_table(VpcId=vpc.id)

    association_id1 = client.associate_route_table(
        RouteTableId=route_table1.id, SubnetId=subnet1.id
    )["AssociationId"]
    client.associate_route_table(RouteTableId=route_table1.id, SubnetId=subnet2.id)
    client.associate_route_table(RouteTableId=route_table2.id, SubnetId=subnet3.id)

    # Filter by association ID
    association1_route_tables = client.describe_route_tables(
        Filters=[
            {
                "Name": "association.route-table-association-id",
                "Values": [association_id1],
            }
        ]
    )["RouteTables"]
    association1_route_tables.should.have.length_of(1)
    association1_route_tables[0]["RouteTableId"].should.equal(route_table1.id)
    association1_route_tables[0]["Associations"].should.have.length_of(3)

    # Filter by route table ID
    route_table2_route_tables = client.describe_route_tables(
        Filters=[{"Name": "association.route-table-id", "Values": [route_table2.id]}]
    )["RouteTables"]
    route_table2_route_tables.should.have.length_of(1)
    route_table2_route_tables[0]["RouteTableId"].should.equal(route_table2.id)
    route_table2_route_tables[0]["Associations"].should.have.length_of(2)

    # Filter by subnet ID
    subnet_route_tables = client.describe_route_tables(
        Filters=[{"Name": "association.subnet-id", "Values": [subnet1.id]}]
    )["RouteTables"]
    subnet_route_tables.should.have.length_of(1)
    subnet_route_tables[0]["RouteTableId"].should.equal(route_table1.id)
    subnet_route_tables[0]["Associations"].should.have.length_of(3)


# Has boto3 equivalent
@mock_ec2_deprecated
def test_route_table_associations():
    conn = boto.connect_vpc("the_key", "the_secret")
    vpc = conn.create_vpc("10.0.0.0/16")
    subnet = conn.create_subnet(vpc.id, "10.0.0.0/18")
    route_table = conn.create_route_table(vpc.id)

    all_route_tables = conn.get_all_route_tables()
    all_route_tables.should.have.length_of(3)

    # Refresh
    route_table = conn.get_all_route_tables(route_table.id)[0]
    route_table.associations.should.have.length_of(1)

    # Associate
    association_id = conn.associate_route_table(route_table.id, subnet.id)

    # Refresh
    route_table = conn.get_all_route_tables(route_table.id)[0]
    route_table.associations.should.have.length_of(2)

    route_table.associations[1].id.should.equal(association_id)
    route_table.associations[1].main.should.equal(False)
    route_table.associations[1].route_table_id.should.equal(route_table.id)
    route_table.associations[1].subnet_id.should.equal(subnet.id)

    # Associate is idempotent
    association_id_idempotent = conn.associate_route_table(route_table.id, subnet.id)
    association_id_idempotent.should.equal(association_id)

    # Error: Attempt delete associated route table.
    with pytest.raises(EC2ResponseError) as cm:
        conn.delete_route_table(route_table.id)
    cm.value.code.should.equal("DependencyViolation")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none

    # Disassociate
    conn.disassociate_route_table(association_id)

    # Refresh
    route_table = conn.get_all_route_tables(route_table.id)[0]
    route_table.associations.should.have.length_of(1)

    # Error: Disassociate with invalid association ID
    with pytest.raises(EC2ResponseError) as cm:
        conn.disassociate_route_table(association_id)
    cm.value.code.should.equal("InvalidAssociationID.NotFound")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none

    # Error: Associate with invalid subnet ID
    with pytest.raises(EC2ResponseError) as cm:
        conn.associate_route_table(route_table.id, "subnet-1234abcd")
    cm.value.code.should.equal("InvalidSubnetID.NotFound")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none

    # Error: Associate with invalid route table ID
    with pytest.raises(EC2ResponseError) as cm:
        conn.associate_route_table("rtb-1234abcd", subnet.id)
    cm.value.code.should.equal("InvalidRouteTableID.NotFound")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none


@mock_ec2
def test_route_table_associations_boto3():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock="10.0.0.0/18")
    route_table = ec2.create_route_table(VpcId=vpc.id)

    # Refresh
    r = client.describe_route_tables(RouteTableIds=[route_table.id])["RouteTables"][0]
    r["Associations"].should.have.length_of(1)
    print(r)

    # Associate
    association_id = client.associate_route_table(
        RouteTableId=route_table.id, SubnetId=subnet.id
    )["AssociationId"]

    # Refresh
    r = client.describe_route_tables(RouteTableIds=[route_table.id])["RouteTables"][0]
    r["Associations"].should.have.length_of(2)

    r["Associations"][1]["RouteTableAssociationId"].should.equal(association_id)
    r["Associations"][1]["Main"].should.equal(False)
    r["Associations"][1]["RouteTableId"].should.equal(route_table.id)
    r["Associations"][1]["SubnetId"].should.equal(subnet.id)

    # Associate is idempotent
    association_id_idempotent = client.associate_route_table(
        RouteTableId=route_table.id, SubnetId=subnet.id
    )["AssociationId"]
    association_id_idempotent.should.equal(association_id)

    # Error: Attempt delete associated route table.
    with pytest.raises(ClientError) as ex:
        client.delete_route_table(RouteTableId=route_table.id)
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("DependencyViolation")

    # Disassociate
    client.disassociate_route_table(AssociationId=association_id)

    # Refresh - The default (main) route should be there
    r = client.describe_route_tables(RouteTableIds=[route_table.id])["RouteTables"][0]
    r["Associations"].should.have.length_of(1)
    r["Associations"][0].should.have.key("Main").equal(True)
    r["Associations"][0].should.have.key("RouteTableAssociationId")
    r["Associations"][0].should.have.key("RouteTableId").equals(route_table.id)
    r["Associations"][0].should.have.key("AssociationState").equals(
        {"State": "associated"}
    )
    r["Associations"][0].shouldnt.have.key("SubnetId")

    # Error: Disassociate with invalid association ID
    with pytest.raises(ClientError) as ex:
        client.disassociate_route_table(AssociationId=association_id)
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("InvalidAssociationID.NotFound")

    # Error: Associate with invalid subnet ID
    with pytest.raises(ClientError) as ex:
        client.associate_route_table(
            RouteTableId=route_table.id, SubnetId="subnet-1234abcd"
        )
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("InvalidSubnetID.NotFound")

    # Error: Associate with invalid route table ID
    with pytest.raises(ClientError) as ex:
        client.associate_route_table(RouteTableId="rtb-1234abcd", SubnetId=subnet.id)
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("InvalidRouteTableID.NotFound")


# Has boto3 equivalent
@requires_boto_gte("2.16.0")
@mock_ec2_deprecated
def test_route_table_replace_route_table_association():
    """
    Note: Boto has deprecated replace_route_table_association (which returns status)
      and now uses replace_route_table_association_with_assoc (which returns association ID).
    """
    conn = boto.connect_vpc("the_key", "the_secret")
    vpc = conn.create_vpc("10.0.0.0/16")
    subnet = conn.create_subnet(vpc.id, "10.0.0.0/18")
    route_table1 = conn.create_route_table(vpc.id)
    route_table2 = conn.create_route_table(vpc.id)

    all_route_tables = conn.get_all_route_tables()
    all_route_tables.should.have.length_of(4)

    # Refresh
    route_table1 = conn.get_all_route_tables(route_table1.id)[0]
    route_table1.associations.should.have.length_of(1)

    # Associate
    association_id1 = conn.associate_route_table(route_table1.id, subnet.id)

    # Refresh
    route_table1 = conn.get_all_route_tables(route_table1.id)[0]
    route_table2 = conn.get_all_route_tables(route_table2.id)[0]

    # Validate
    route_table1.associations.should.have.length_of(2)
    route_table2.associations.should.have.length_of(1)

    route_table1.associations[1].id.should.equal(association_id1)
    route_table1.associations[1].main.should.equal(False)
    route_table1.associations[1].route_table_id.should.equal(route_table1.id)
    route_table1.associations[1].subnet_id.should.equal(subnet.id)

    # Replace Association
    association_id2 = conn.replace_route_table_association_with_assoc(
        association_id1, route_table2.id
    )

    # Refresh
    route_table1 = conn.get_all_route_tables(route_table1.id)[0]
    route_table2 = conn.get_all_route_tables(route_table2.id)[0]

    # Validate
    route_table1.associations.should.have.length_of(1)
    route_table2.associations.should.have.length_of(2)

    route_table2.associations[1].id.should.equal(association_id2)
    route_table2.associations[1].main.should.equal(False)
    route_table2.associations[1].route_table_id.should.equal(route_table2.id)
    route_table2.associations[1].subnet_id.should.equal(subnet.id)

    # Replace Association is idempotent
    association_id_idempotent = conn.replace_route_table_association_with_assoc(
        association_id2, route_table2.id
    )
    association_id_idempotent.should.equal(association_id2)

    # Error: Replace association with invalid association ID
    with pytest.raises(EC2ResponseError) as cm:
        conn.replace_route_table_association_with_assoc(
            "rtbassoc-1234abcd", route_table1.id
        )
    cm.value.code.should.equal("InvalidAssociationID.NotFound")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none

    # Error: Replace association with invalid route table ID
    with pytest.raises(EC2ResponseError) as cm:
        conn.replace_route_table_association_with_assoc(association_id2, "rtb-1234abcd")
    cm.value.code.should.equal("InvalidRouteTableID.NotFound")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none


@mock_ec2
def test_route_table_replace_route_table_association_boto3():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock="10.0.0.0/18")
    route_table1_id = ec2.create_route_table(VpcId=vpc.id).id
    route_table2_id = ec2.create_route_table(VpcId=vpc.id).id

    all_route_tables = client.describe_route_tables()["RouteTables"]
    all_ids = [rt["RouteTableId"] for rt in all_route_tables]
    all_ids.should.contain(route_table1_id)
    all_ids.should.contain(route_table2_id)

    # Refresh
    route_table1 = client.describe_route_tables(RouteTableIds=[route_table1_id])[
        "RouteTables"
    ][0]
    route_table1["Associations"].should.have.length_of(1)

    # Associate
    association_id1 = client.associate_route_table(
        RouteTableId=route_table1_id, SubnetId=subnet.id
    )["AssociationId"]

    # Refresh
    route_table1 = client.describe_route_tables(RouteTableIds=[route_table1_id])[
        "RouteTables"
    ][0]
    route_table2 = client.describe_route_tables(RouteTableIds=[route_table2_id])[
        "RouteTables"
    ][0]

    # Validate
    route_table1["Associations"].should.have.length_of(2)
    route_table2["Associations"].should.have.length_of(1)

    route_table1["Associations"][1]["RouteTableAssociationId"].should.equal(
        association_id1
    )
    route_table1["Associations"][1]["Main"].should.equal(False)
    route_table1["Associations"][1]["RouteTableId"].should.equal(route_table1_id)
    route_table1["Associations"][1]["SubnetId"].should.equal(subnet.id)

    # Replace Association
    association_id2 = client.replace_route_table_association(
        AssociationId=association_id1, RouteTableId=route_table2_id
    )["NewAssociationId"]

    # Refresh
    route_table1 = client.describe_route_tables(RouteTableIds=[route_table1_id])[
        "RouteTables"
    ][0]
    route_table2 = client.describe_route_tables(RouteTableIds=[route_table2_id])[
        "RouteTables"
    ][0]

    # Validate
    route_table1["Associations"].should.have.length_of(1)
    route_table2["Associations"].should.have.length_of(2)

    route_table2["Associations"][1]["RouteTableAssociationId"].should.equal(
        association_id2
    )
    route_table2["Associations"][1]["Main"].should.equal(False)
    route_table2["Associations"][1]["RouteTableId"].should.equal(route_table2_id)
    route_table2["Associations"][1]["SubnetId"].should.equal(subnet.id)

    # Replace Association is idempotent
    association_id_idempotent = client.replace_route_table_association(
        AssociationId=association_id2, RouteTableId=route_table2_id
    )["NewAssociationId"]
    association_id_idempotent.should.equal(association_id2)

    # Error: Replace association with invalid association ID
    with pytest.raises(ClientError) as ex:
        client.replace_route_table_association(
            AssociationId="rtbassoc-1234abcd", RouteTableId=route_table1_id
        )
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("InvalidAssociationID.NotFound")

    # Error: Replace association with invalid route table ID
    with pytest.raises(ClientError) as ex:
        client.replace_route_table_association(
            AssociationId=association_id2, RouteTableId="rtb-1234abcd"
        )
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("InvalidRouteTableID.NotFound")


# Has boto3 equivalent
@mock_ec2_deprecated
def test_route_table_get_by_tag():
    conn = boto.connect_vpc("the_key", "the_secret")

    vpc = conn.create_vpc("10.0.0.0/16")

    route_table = conn.create_route_table(vpc.id)
    route_table.add_tag("Name", "TestRouteTable")

    route_tables = conn.get_all_route_tables(filters={"tag:Name": "TestRouteTable"})

    route_tables.should.have.length_of(1)
    route_tables[0].vpc_id.should.equal(vpc.id)
    route_tables[0].id.should.equal(route_table.id)
    route_tables[0].tags.should.have.length_of(1)
    route_tables[0].tags["Name"].should.equal("TestRouteTable")


@mock_ec2
def test_route_table_get_by_tag_boto3():
    ec2 = boto3.resource("ec2", region_name="eu-central-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")

    route_table = ec2.create_route_table(VpcId=vpc.id)
    tag_value = str(uuid4())
    route_table.create_tags(Tags=[{"Key": "Name", "Value": tag_value}])

    filters = [{"Name": "tag:Name", "Values": [tag_value]}]
    route_tables = list(ec2.route_tables.filter(Filters=filters))

    route_tables.should.have.length_of(1)
    route_tables[0].vpc_id.should.equal(vpc.id)
    route_tables[0].id.should.equal(route_table.id)
    route_tables[0].tags.should.have.length_of(1)
    route_tables[0].tags[0].should.equal({"Key": "Name", "Value": tag_value})


# Has boto3 equivalent
@mock_ec2_deprecated
def test_routes_additional():
    conn = boto.connect_vpc("the_key", "the_secret")
    vpc = conn.create_vpc("10.0.0.0/16")
    main_route_table = conn.get_all_route_tables(filters={"vpc-id": vpc.id})[0]

    igw = conn.create_internet_gateway()
    ROUTE_CIDR = "10.0.0.4/24"

    conn.create_route(main_route_table.id, ROUTE_CIDR, gateway_id=igw.id)

    main_route_table = conn.get_all_route_tables(filters={"vpc-id": vpc.id})[
        0
    ]  # Refresh route table

    main_route_table.routes.should.have.length_of(2)
    new_routes = [
        route
        for route in main_route_table.routes
        if route.destination_cidr_block != vpc.cidr_block
    ]
    new_routes.should.have.length_of(1)

    new_route = new_routes[0]
    new_route.gateway_id.should.equal(igw.id)
    new_route.instance_id.should.be.none
    new_route.state.should.equal("active")
    new_route.destination_cidr_block.should.equal(ROUTE_CIDR)

    conn.delete_route(main_route_table.id, ROUTE_CIDR)

    main_route_table = conn.get_all_route_tables(filters={"vpc-id": vpc.id})[
        0
    ]  # Refresh route table

    main_route_table.routes.should.have.length_of(1)
    new_routes = [
        route
        for route in main_route_table.routes
        if route.destination_cidr_block != vpc.cidr_block
    ]
    new_routes.should.have.length_of(0)

    with pytest.raises(EC2ResponseError) as cm:
        conn.delete_route(main_route_table.id, ROUTE_CIDR)
    cm.value.code.should.equal("InvalidRoute.NotFound")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none


@mock_ec2
def test_routes_additional_boto3():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    main_route_table_id = client.describe_route_tables(
        Filters=[{"Name": "vpc-id", "Values": [vpc.id]}]
    )["RouteTables"][0]["RouteTableId"]
    main_route_table = ec2.RouteTable(main_route_table_id)

    main_route_table.routes.should.have.length_of(1)
    igw = ec2.create_internet_gateway()
    ROUTE_CIDR = "10.0.0.4/24"

    main_route_table.create_route(DestinationCidrBlock=ROUTE_CIDR, GatewayId=igw.id)

    main_route_table.routes.should.have.length_of(2)
    new_routes = [
        route
        for route in main_route_table.routes
        if route.destination_cidr_block != vpc.cidr_block
    ]
    new_routes.should.have.length_of(1)

    new_route = new_routes[0]
    new_route.gateway_id.should.equal(igw.id)
    new_route.instance_id.should.be.none
    new_route.state.should.equal("active")
    new_route.destination_cidr_block.should.equal(ROUTE_CIDR)

    client.delete_route(
        RouteTableId=main_route_table.id, DestinationCidrBlock=ROUTE_CIDR
    )

    main_route_table.reload()

    main_route_table.routes.should.have.length_of(1)
    new_routes = [
        route
        for route in main_route_table.routes
        if route.destination_cidr_block != vpc.cidr_block
    ]
    new_routes.should.have.length_of(0)

    with pytest.raises(ClientError) as ex:
        client.delete_route(
            RouteTableId=main_route_table.id, DestinationCidrBlock=ROUTE_CIDR
        )
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("InvalidRoute.NotFound")


# Has boto3 equivalent
@mock_ec2_deprecated
def test_routes_replace():
    conn = boto.connect_vpc("the_key", "the_secret")
    vpc = conn.create_vpc("10.0.0.0/16")
    main_route_table = conn.get_all_route_tables(
        filters={"association.main": "true", "vpc-id": vpc.id}
    )[0]

    ROUTE_CIDR = "10.0.0.4/24"

    # Various route targets
    igw = conn.create_internet_gateway()

    reservation = conn.run_instances(EXAMPLE_AMI_ID)
    instance = reservation.instances[0]

    # Create initial route
    conn.create_route(main_route_table.id, ROUTE_CIDR, gateway_id=igw.id)

    # Replace...
    def get_target_route():
        route_table = conn.get_all_route_tables(main_route_table.id)[0]
        routes = [
            route
            for route in route_table.routes
            if route.destination_cidr_block != vpc.cidr_block
        ]
        routes.should.have.length_of(1)
        return routes[0]

    conn.replace_route(main_route_table.id, ROUTE_CIDR, instance_id=instance.id)

    target_route = get_target_route()
    target_route.gateway_id.should.be.none
    target_route.instance_id.should.equal(instance.id)
    target_route.state.should.equal("active")
    target_route.destination_cidr_block.should.equal(ROUTE_CIDR)

    conn.replace_route(main_route_table.id, ROUTE_CIDR, gateway_id=igw.id)

    target_route = get_target_route()
    target_route.gateway_id.should.equal(igw.id)
    target_route.instance_id.should.be.none
    target_route.state.should.equal("active")
    target_route.destination_cidr_block.should.equal(ROUTE_CIDR)

    with pytest.raises(EC2ResponseError) as cm:
        conn.replace_route("rtb-1234abcd", ROUTE_CIDR, gateway_id=igw.id)
    cm.value.code.should.equal("InvalidRouteTableID.NotFound")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none


@mock_ec2
def test_routes_replace_boto3():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")

    main_route_table_id = client.describe_route_tables(
        Filters=[
            {"Name": "vpc-id", "Values": [vpc.id]},
            {"Name": "association.main", "Values": ["true"]},
        ]
    )["RouteTables"][0]["RouteTableId"]
    main_route_table = ec2.RouteTable(main_route_table_id)
    ROUTE_CIDR = "10.0.0.4/24"

    # Various route targets
    igw = ec2.create_internet_gateway()

    instance = ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)[0]

    # Create initial route
    main_route_table.create_route(DestinationCidrBlock=ROUTE_CIDR, GatewayId=igw.id)

    # Replace...
    def get_target_route():
        route_table = client.describe_route_tables(RouteTableIds=[main_route_table.id])[
            "RouteTables"
        ][0]
        routes = [
            route
            for route in route_table["Routes"]
            if route["DestinationCidrBlock"] != vpc.cidr_block
        ]
        routes.should.have.length_of(1)
        return routes[0]

    client.replace_route(
        RouteTableId=main_route_table.id,
        DestinationCidrBlock=ROUTE_CIDR,
        InstanceId=instance.id,
    )

    target_route = get_target_route()
    target_route.shouldnt.have.key("GatewayId")
    target_route["InstanceId"].should.equal(instance.id)
    target_route["State"].should.equal("active")
    target_route["DestinationCidrBlock"].should.equal(ROUTE_CIDR)

    client.replace_route(
        RouteTableId=main_route_table.id,
        DestinationCidrBlock=ROUTE_CIDR,
        GatewayId=igw.id,
    )

    target_route = get_target_route()
    target_route["GatewayId"].should.equal(igw.id)
    target_route.shouldnt.have.key("InstanceId")
    target_route["State"].should.equal("active")
    target_route["DestinationCidrBlock"].should.equal(ROUTE_CIDR)

    with pytest.raises(ClientError) as ex:
        client.replace_route(
            RouteTableId="rtb-1234abcd",
            DestinationCidrBlock=ROUTE_CIDR,
            GatewayId=igw.id,
        )
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("InvalidRouteTableID.NotFound")


# Has boto3 equivalent
@requires_boto_gte("2.19.0")
@mock_ec2_deprecated
def test_routes_not_supported():
    conn = boto.connect_vpc("the_key", "the_secret")
    conn.create_vpc("10.0.0.0/16")
    main_route_table = conn.get_all_route_tables()[0]

    conn.create_internet_gateway()
    ROUTE_CIDR = "10.0.0.4/24"

    # Create
    conn.create_route.when.called_with(
        main_route_table.id, ROUTE_CIDR, interface_id="eni-1234abcd"
    ).should.throw("InvalidNetworkInterfaceID.NotFound")

    # Replace
    igw = conn.create_internet_gateway()
    conn.create_route(main_route_table.id, ROUTE_CIDR, gateway_id=igw.id)
    conn.replace_route.when.called_with(
        main_route_table.id, ROUTE_CIDR, interface_id="eni-1234abcd"
    ).should.throw(NotImplementedError)


@mock_ec2
def test_routes_not_supported_boto3():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    main_route_table_id = client.describe_route_tables()["RouteTables"][0][
        "RouteTableId"
    ]
    main_route_table = ec2.RouteTable(main_route_table_id)

    ROUTE_CIDR = "10.0.0.4/24"

    # Create
    with pytest.raises(ClientError) as ex:
        client.create_route(
            RouteTableId=main_route_table_id,
            DestinationCidrBlock=ROUTE_CIDR,
            NetworkInterfaceId="eni-1234abcd",
        )
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal(
        "InvalidNetworkInterfaceID.NotFound"
    )

    igw = ec2.create_internet_gateway()
    client.create_route(
        RouteTableId=main_route_table_id,
        DestinationCidrBlock=ROUTE_CIDR,
        GatewayId=igw.id,
    )

    # Replace
    if not settings.TEST_SERVER_MODE:
        args = {
            "RouteTableId": main_route_table.id,
            "DestinationCidrBlock": ROUTE_CIDR,
            "NetworkInterfaceId": "eni-1234abcd",
        }
        client.replace_route.when.called_with(**args).should.throw(NotImplementedError)


# Has boto3 equivalent
@requires_boto_gte("2.34.0")
@mock_ec2_deprecated
def test_routes_vpc_peering_connection():
    conn = boto.connect_vpc("the_key", "the_secret")
    vpc = conn.create_vpc("10.0.0.0/16")
    main_route_table = conn.get_all_route_tables(
        filters={"association.main": "true", "vpc-id": vpc.id}
    )[0]

    ROUTE_CIDR = "10.0.0.4/24"

    peer_vpc = conn.create_vpc("11.0.0.0/16")
    vpc_pcx = conn.create_vpc_peering_connection(vpc.id, peer_vpc.id)

    conn.create_route(
        main_route_table.id, ROUTE_CIDR, vpc_peering_connection_id=vpc_pcx.id
    )

    # Refresh route table
    main_route_table = conn.get_all_route_tables(main_route_table.id)[0]
    new_routes = [
        route
        for route in main_route_table.routes
        if route.destination_cidr_block != vpc.cidr_block
    ]
    new_routes.should.have.length_of(1)

    new_route = new_routes[0]
    new_route.gateway_id.should.be.none
    new_route.instance_id.should.be.none
    new_route.vpc_peering_connection_id.should.equal(vpc_pcx.id)
    new_route.state.should.equal("active")
    new_route.destination_cidr_block.should.equal(ROUTE_CIDR)


@mock_ec2
def test_routes_vpc_peering_connection_boto3():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    main_route_table_id = client.describe_route_tables(
        Filters=[
            {"Name": "vpc-id", "Values": [vpc.id]},
            {"Name": "association.main", "Values": ["true"]},
        ]
    )["RouteTables"][0]["RouteTableId"]
    main_route_table = ec2.RouteTable(main_route_table_id)
    ROUTE_CIDR = "10.0.0.4/24"

    peer_vpc = ec2.create_vpc(CidrBlock="11.0.0.0/16")
    vpc_pcx = ec2.create_vpc_peering_connection(VpcId=vpc.id, PeerVpcId=peer_vpc.id)

    main_route_table.create_route(
        DestinationCidrBlock=ROUTE_CIDR, VpcPeeringConnectionId=vpc_pcx.id
    )

    # Refresh route table
    main_route_table.reload()
    new_routes = [
        route
        for route in main_route_table.routes
        if route.destination_cidr_block != vpc.cidr_block
    ]
    new_routes.should.have.length_of(1)

    new_route = new_routes[0]
    new_route.gateway_id.should.be.none
    new_route.instance_id.should.be.none
    new_route.vpc_peering_connection_id.should.equal(vpc_pcx.id)
    new_route.state.should.equal("active")
    new_route.destination_cidr_block.should.equal(ROUTE_CIDR)


# Has boto3 equivalent
@requires_boto_gte("2.34.0")
@mock_ec2_deprecated
def test_routes_vpn_gateway():

    conn = boto.connect_vpc("the_key", "the_secret")
    vpc = conn.create_vpc("10.0.0.0/16")
    main_route_table = conn.get_all_route_tables(
        filters={"association.main": "true", "vpc-id": vpc.id}
    )[0]
    ROUTE_CIDR = "10.0.0.4/24"

    vpn_gw = conn.create_vpn_gateway(type="ipsec.1")

    conn.create_route(main_route_table.id, ROUTE_CIDR, gateway_id=vpn_gw.id)

    main_route_table = conn.get_all_route_tables(main_route_table.id)[0]
    new_routes = [
        route
        for route in main_route_table.routes
        if route.destination_cidr_block != vpc.cidr_block
    ]
    new_routes.should.have.length_of(1)

    new_route = new_routes[0]
    new_route.gateway_id.should.equal(vpn_gw.id)
    new_route.instance_id.should.be.none
    new_route.vpc_peering_connection_id.should.be.none


@mock_ec2
def test_routes_vpn_gateway_boto3():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")

    main_route_table_id = client.describe_route_tables(
        Filters=[
            {"Name": "vpc-id", "Values": [vpc.id]},
            {"Name": "association.main", "Values": ["true"]},
        ]
    )["RouteTables"][0]["RouteTableId"]
    main_route_table = ec2.RouteTable(main_route_table_id)
    ROUTE_CIDR = "10.0.0.4/24"

    vpn_gw_id = client.create_vpn_gateway(Type="ipsec.1")["VpnGateway"]["VpnGatewayId"]

    main_route_table.create_route(DestinationCidrBlock=ROUTE_CIDR, GatewayId=vpn_gw_id)

    main_route_table.reload()
    new_routes = [
        route
        for route in main_route_table.routes
        if route.destination_cidr_block != vpc.cidr_block
    ]
    new_routes.should.have.length_of(1)

    new_route = new_routes[0]
    new_route.gateway_id.should.equal(vpn_gw_id)
    new_route.instance_id.should.be.none
    new_route.vpc_peering_connection_id.should.be.none


# Has boto3 equivalent
@mock_ec2_deprecated
def test_network_acl_tagging():

    conn = boto.connect_vpc("the_key", "the secret")
    vpc = conn.create_vpc("10.0.0.0/16")

    route_table = conn.create_route_table(vpc.id)
    route_table.add_tag("a key", "some value")

    tag = conn.get_all_tags()[0]
    tag.name.should.equal("a key")
    tag.value.should.equal("some value")

    all_route_tables = conn.get_all_route_tables()
    test_route_table = next(na for na in all_route_tables if na.id == route_table.id)
    test_route_table.tags.should.have.length_of(1)
    test_route_table.tags["a key"].should.equal("some value")


@mock_ec2
def test_network_acl_tagging_boto3():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")

    route_table = ec2.create_route_table(VpcId=vpc.id)
    route_table.create_tags(Tags=[{"Key": "a key", "Value": "some value"}])

    tag = client.describe_tags(
        Filters=[{"Name": "resource-id", "Values": [route_table.id]}]
    )["Tags"][0]
    tag.should.have.key("ResourceType").equal("route-table")
    tag.should.have.key("Key").equal("a key")
    tag.should.have.key("Value").equal("some value")

    all_route_tables = client.describe_route_tables()["RouteTables"]
    test_route_table = next(
        na for na in all_route_tables if na["RouteTableId"] == route_table.id
    )
    test_route_table["Tags"].should.equal([{"Value": "some value", "Key": "a key"}])


@mock_ec2
def test_create_route_with_invalid_destination_cidr_block_parameter():
    ec2 = boto3.resource("ec2", region_name="us-west-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    vpc.reload()
    vpc.is_default.shouldnt.be.ok

    route_table = ec2.create_route_table(VpcId=vpc.id)
    route_table.reload()

    internet_gateway = ec2.create_internet_gateway()
    vpc.attach_internet_gateway(InternetGatewayId=internet_gateway.id)
    internet_gateway.reload()

    destination_cidr_block = "1000.1.0.0/20"
    with pytest.raises(ClientError) as ex:
        route = route_table.create_route(
            DestinationCidrBlock=destination_cidr_block, GatewayId=internet_gateway.id
        )
    str(ex.value).should.equal(
        "An error occurred (InvalidParameterValue) when calling the CreateRoute "
        "operation: Value ({}) for parameter destinationCidrBlock is invalid. This is not a valid CIDR block.".format(
            destination_cidr_block
        )
    )

    route_table.create_route(
        DestinationIpv6CidrBlock="2001:db8::/125", GatewayId=internet_gateway.id
    )
    new_routes = [
        route
        for route in route_table.routes
        if route.destination_cidr_block != vpc.cidr_block
        or route.destination_ipv6_cidr_block != vpc.cidr_block
    ]
    new_routes.should.have.length_of(1)
    new_routes[0].route_table_id.shouldnt.be.equal(None)


@mock_ec2
def test_create_route_with_network_interface_id():
    ec2 = boto3.resource("ec2", region_name="us-west-2")
    ec2_client = boto3.client("ec2", region_name="us-west-2")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="10.0.0.0/24", AvailabilityZone="us-west-2a"
    )

    route_table = ec2_client.create_route_table(VpcId=vpc.id)

    route_table_id = route_table["RouteTable"]["RouteTableId"]

    eni1 = ec2_client.create_network_interface(
        SubnetId=subnet.id, PrivateIpAddress="10.0.10.5"
    )

    route = ec2_client.create_route(
        NetworkInterfaceId=eni1["NetworkInterface"]["NetworkInterfaceId"],
        RouteTableId=route_table_id,
    )

    route["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)


@mock_ec2
def test_describe_route_tables_with_nat_gateway():
    ec2 = boto3.client("ec2", region_name="us-west-1")
    vpc_id = ec2.create_vpc(CidrBlock="192.168.0.0/23")["Vpc"]["VpcId"]
    igw_id = ec2.create_internet_gateway()["InternetGateway"]["InternetGatewayId"]
    ec2.attach_internet_gateway(VpcId=vpc_id, InternetGatewayId=igw_id)
    az = ec2.describe_availability_zones()["AvailabilityZones"][0]["ZoneName"]
    sn_id = ec2.create_subnet(
        AvailabilityZone=az, CidrBlock="192.168.0.0/24", VpcId=vpc_id
    )["Subnet"]["SubnetId"]
    route_table_id = ec2.create_route_table(VpcId=vpc_id)["RouteTable"]["RouteTableId"]
    ec2.associate_route_table(SubnetId=sn_id, RouteTableId=route_table_id)
    alloc_id = ec2.allocate_address(Domain="vpc")["AllocationId"]
    nat_gw_id = ec2.create_nat_gateway(SubnetId=sn_id, AllocationId=alloc_id)[
        "NatGateway"
    ]["NatGatewayId"]
    ec2.create_route(
        DestinationCidrBlock="0.0.0.0/0",
        NatGatewayId=nat_gw_id,
        RouteTableId=route_table_id,
    )

    route_table = ec2.describe_route_tables(
        Filters=[{"Name": "route-table-id", "Values": [route_table_id]}]
    )["RouteTables"][0]
    nat_gw_routes = [
        route
        for route in route_table["Routes"]
        if route["DestinationCidrBlock"] == "0.0.0.0/0"
    ]

    nat_gw_routes.should.have.length_of(1)
    nat_gw_routes[0]["DestinationCidrBlock"].should.equal("0.0.0.0/0")
    nat_gw_routes[0]["NatGatewayId"].should.equal(nat_gw_id)
    nat_gw_routes[0]["State"].should.equal("active")


@mock_ec2
def test_create_vpc_end_point():

    ec2 = boto3.client("ec2", region_name="us-west-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(VpcId=vpc["Vpc"]["VpcId"], CidrBlock="10.0.0.0/24")

    route_table = ec2.create_route_table(VpcId=vpc["Vpc"]["VpcId"])

    # test without any end point type specified
    vpc_end_point = ec2.create_vpc_endpoint(
        VpcId=vpc["Vpc"]["VpcId"],
        ServiceName="com.amazonaws.us-east-1.s3",
        RouteTableIds=[route_table["RouteTable"]["RouteTableId"]],
    )

    vpc_end_point["VpcEndpoint"]["ServiceName"].should.equal(
        "com.amazonaws.us-east-1.s3"
    )
    vpc_end_point["VpcEndpoint"]["RouteTableIds"][0].should.equal(
        route_table["RouteTable"]["RouteTableId"]
    )
    vpc_end_point["VpcEndpoint"]["VpcId"].should.equal(vpc["Vpc"]["VpcId"])
    vpc_end_point["VpcEndpoint"]["DnsEntries"].should.have.length_of(0)

    # test with any end point type as gateway
    vpc_end_point = ec2.create_vpc_endpoint(
        VpcId=vpc["Vpc"]["VpcId"],
        ServiceName="com.amazonaws.us-east-1.s3",
        RouteTableIds=[route_table["RouteTable"]["RouteTableId"]],
        VpcEndpointType="gateway",
    )

    vpc_end_point["VpcEndpoint"]["ServiceName"].should.equal(
        "com.amazonaws.us-east-1.s3"
    )
    vpc_end_point["VpcEndpoint"]["RouteTableIds"][0].should.equal(
        route_table["RouteTable"]["RouteTableId"]
    )
    vpc_end_point["VpcEndpoint"]["VpcId"].should.equal(vpc["Vpc"]["VpcId"])
    vpc_end_point["VpcEndpoint"]["DnsEntries"].should.have.length_of(0)

    # test with end point type as interface
    vpc_end_point = ec2.create_vpc_endpoint(
        VpcId=vpc["Vpc"]["VpcId"],
        ServiceName="com.amazonaws.us-east-1.s3",
        SubnetIds=[subnet["Subnet"]["SubnetId"]],
        VpcEndpointType="interface",
    )

    vpc_end_point["VpcEndpoint"]["ServiceName"].should.equal(
        "com.amazonaws.us-east-1.s3"
    )
    vpc_end_point["VpcEndpoint"]["SubnetIds"][0].should.equal(
        subnet["Subnet"]["SubnetId"]
    )
    vpc_end_point["VpcEndpoint"]["VpcId"].should.equal(vpc["Vpc"]["VpcId"])
    len(vpc_end_point["VpcEndpoint"]["DnsEntries"]).should.be.greater_than(0)


@mock_ec2
def test_create_route_tables_with_tags():
    ec2 = boto3.resource("ec2", region_name="eu-central-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")

    route_table = ec2.create_route_table(
        VpcId=vpc.id,
        TagSpecifications=[
            {
                "ResourceType": "route-table",
                "Tags": [{"Key": "test", "Value": "TestRouteTable"}],
            }
        ],
    )

    route_table.tags.should.have.length_of(1)


@mock_ec2
def test_create_route_with_egress_only_igw():
    ec2 = boto3.resource("ec2", region_name="eu-central-1")
    ec2_client = boto3.client("ec2", region_name="eu-central-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    eigw = ec2_client.create_egress_only_internet_gateway(VpcId=vpc.id)
    eigw_id = eigw["EgressOnlyInternetGateway"]["EgressOnlyInternetGatewayId"]

    route_table = ec2.create_route_table(VpcId=vpc.id)

    ec2_client.create_route(
        RouteTableId=route_table.id,
        EgressOnlyInternetGatewayId=eigw_id,
        DestinationIpv6CidrBlock="::/0",
    )

    route_table.reload()
    eigw_route = [
        r
        for r in route_table.routes_attribute
        if r.get("DestinationIpv6CidrBlock") == "::/0"
    ][0]
    eigw_route.get("EgressOnlyInternetGatewayId").should.equal(eigw_id)
    eigw_route.get("State").should.equal("active")


@mock_ec2
def test_create_route_with_unknown_egress_only_igw():
    ec2 = boto3.resource("ec2", region_name="eu-central-1")
    ec2_client = boto3.client("ec2", region_name="eu-central-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="10.0.0.0/24", AvailabilityZone="us-west-2a"
    )

    route_table = ec2.create_route_table(VpcId=vpc.id)

    with pytest.raises(ClientError) as ex:
        ec2_client.create_route(
            RouteTableId=route_table.id, EgressOnlyInternetGatewayId="eoigw"
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("InvalidGatewayID.NotFound")
    err["Message"].should.equal("The eigw ID 'eoigw' does not exist")


@mock_ec2
def test_associate_route_table_by_gateway():
    ec2 = boto3.client("ec2", region_name="us-west-1")
    vpc_id = ec2.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]["VpcId"]
    route_table_id = ec2.create_route_table(VpcId=vpc_id)["RouteTable"]["RouteTableId"]
    igw_id = ec2.create_internet_gateway()["InternetGateway"]["InternetGatewayId"]
    assoc_id = ec2.associate_route_table(
        RouteTableId=route_table_id, GatewayId=igw_id,
    )["AssociationId"]
    verify = ec2.describe_route_tables(
        Filters=[
            {"Name": "association.route-table-association-id", "Values": [assoc_id]}
        ]
    )["RouteTables"]

    # First assocation is the main
    verify[0]["Associations"][0]["Main"].should.equal(True)

    # Second is our Gateway
    verify[0]["Associations"][1]["Main"].should.equal(False)
    verify[0]["Associations"][1]["GatewayId"].should.equal(igw_id)
    verify[0]["Associations"][1]["RouteTableAssociationId"].should.equal(assoc_id)
    verify[0]["Associations"][1].doesnt.have.key("SubnetId")


@mock_ec2
def test_associate_route_table_by_subnet():
    ec2 = boto3.client("ec2", region_name="us-west-1")
    vpc_id = ec2.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]["VpcId"]
    route_table_id = ec2.create_route_table(VpcId=vpc_id)["RouteTable"]["RouteTableId"]
    subnet_id = ec2.create_subnet(VpcId=vpc_id, CidrBlock="10.0.0.0/24")["Subnet"][
        "SubnetId"
    ]
    assoc_id = ec2.associate_route_table(
        RouteTableId=route_table_id, SubnetId=subnet_id,
    )["AssociationId"]
    verify = ec2.describe_route_tables(
        Filters=[
            {"Name": "association.route-table-association-id", "Values": [assoc_id]}
        ]
    )["RouteTables"]
    print(verify[0]["Associations"])

    # First assocation is the main
    verify[0]["Associations"][0].should.have.key("Main").equals(True)

    # Second is our Gateway
    verify[0]["Associations"][1]["Main"].should.equal(False)
    verify[0]["Associations"][1]["SubnetId"].should.equals(subnet_id)
    verify[0]["Associations"][1]["RouteTableAssociationId"].should.equal(assoc_id)
    verify[0]["Associations"][1].doesnt.have.key("GatewayId")
