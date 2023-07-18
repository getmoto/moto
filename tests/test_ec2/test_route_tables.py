import boto3
import pytest

from botocore.exceptions import ClientError
from moto import mock_ec2, settings
from tests import EXAMPLE_AMI_ID
from uuid import uuid4


@mock_ec2
def test_route_tables_defaults():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")

    all_route_tables = client.describe_route_tables(
        Filters=[{"Name": "vpc-id", "Values": [vpc.id]}]
    )["RouteTables"]
    assert len(all_route_tables) == 1

    main_route_table = all_route_tables[0]
    assert main_route_table["VpcId"] == vpc.id

    routes = main_route_table["Routes"]
    assert len(routes) == 1

    local_route = routes[0]
    assert local_route["GatewayId"] == "local"
    assert local_route["State"] == "active"
    assert local_route["DestinationCidrBlock"] == vpc.cidr_block

    vpc.delete()

    all_route_tables = client.describe_route_tables(
        Filters=[{"Name": "vpc-id", "Values": [vpc.id]}]
    )["RouteTables"]
    assert len(all_route_tables) == 0


@mock_ec2
def test_route_tables_additional():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    route_table = vpc.create_route_table()

    all_route_tables = client.describe_route_tables(
        Filters=[{"Name": "vpc-id", "Values": [vpc.id]}]
    )["RouteTables"]
    assert len(all_route_tables) == 2
    assert all_route_tables[0]["VpcId"] == vpc.id
    assert all_route_tables[1]["VpcId"] == vpc.id

    all_route_table_ids = [r["RouteTableId"] for r in all_route_tables]
    assert route_table.route_table_id in all_route_table_ids

    routes = route_table.routes
    assert len(routes) == 1

    local_route = routes[0]
    assert local_route.gateway_id == "local"
    assert local_route.state == "active"
    assert local_route.destination_cidr_block == vpc.cidr_block

    with pytest.raises(ClientError) as ex:
        client.delete_vpc(VpcId=vpc.id)
    assert ex.value.response["Error"]["Code"] == "DependencyViolation"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]

    client.delete_route_table(RouteTableId=route_table.route_table_id)

    all_route_tables = client.describe_route_tables(
        Filters=[{"Name": "vpc-id", "Values": [vpc.id]}]
    )["RouteTables"]
    assert len(all_route_tables) == 1

    with pytest.raises(ClientError) as ex:
        client.delete_route_table(RouteTableId="rtb-1234abcd")
    assert ex.value.response["Error"]["Code"] == "InvalidRouteTableID.NotFound"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]


@mock_ec2
def test_route_tables_filters_standard():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    vpc1 = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    route_table1 = ec2.create_route_table(VpcId=vpc1.id)

    vpc2 = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    route_table2 = ec2.create_route_table(VpcId=vpc2.id)
    igw = ec2.create_internet_gateway()
    route_table2.create_route(DestinationCidrBlock="10.0.0.4/24", GatewayId=igw.id)

    all_route_tables = client.describe_route_tables()["RouteTables"]
    all_ids = [rt["RouteTableId"] for rt in all_route_tables]
    assert route_table1.id in all_ids
    assert route_table2.id in all_ids

    # Filter by main route table
    main_route_tables = client.describe_route_tables(
        Filters=[{"Name": "association.main", "Values": ["true"]}]
    )["RouteTables"]
    main_route_table_ids = [
        route_table["RouteTableId"] for route_table in main_route_tables
    ]
    assert route_table1.id not in main_route_table_ids
    assert route_table2.id not in main_route_table_ids

    # Filter by VPC
    vpc1_route_tables = client.describe_route_tables(
        Filters=[{"Name": "vpc-id", "Values": [vpc1.id]}]
    )["RouteTables"]
    assert len(vpc1_route_tables) == 2
    vpc1_route_table_ids = [
        route_table["RouteTableId"] for route_table in vpc1_route_tables
    ]
    assert route_table1.id in vpc1_route_table_ids
    assert route_table2.id not in vpc1_route_table_ids

    # Filter by VPC and main route table
    vpc2_main_route_tables = client.describe_route_tables(
        Filters=[
            {"Name": "association.main", "Values": ["true"]},
            {"Name": "vpc-id", "Values": [vpc2.id]},
        ]
    )["RouteTables"]
    assert len(vpc2_main_route_tables) == 1
    vpc2_main_route_table_ids = [
        route_table["RouteTableId"] for route_table in vpc2_main_route_tables
    ]
    assert route_table1.id not in vpc2_main_route_table_ids
    assert route_table2.id not in vpc2_main_route_table_ids

    # Filter by route gateway id
    resp = client.describe_route_tables(
        Filters=[
            {"Name": "route.gateway-id", "Values": [igw.id]},
        ]
    )["RouteTables"]
    assert any(
        [route["GatewayId"] == igw.id for table in resp for route in table["Routes"]]
    )

    # Filter by route destination CIDR block
    resp = client.describe_route_tables(
        Filters=[
            {"Name": "route.destination-cidr-block", "Values": ["10.0.0.4/24"]},
        ]
    )["RouteTables"]
    assert any([route_table["RouteTableId"] == route_table2.id for route_table in resp])
    assert any(
        [
            route["DestinationCidrBlock"] == "10.0.0.4/24"
            for table in resp
            for route in table["Routes"]
        ]
    )

    # Unsupported filter
    if not settings.TEST_SERVER_MODE:
        # ServerMode will just throw a generic 500
        filters = [{"Name": "not-implemented-filter", "Values": ["foobar"]}]
        with pytest.raises(NotImplementedError):
            client.describe_route_tables(Filters=filters)


@mock_ec2
def test_route_tables_filters_associations():
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
    assert len(association1_route_tables) == 1
    assert association1_route_tables[0]["RouteTableId"] == route_table1.id
    assert len(association1_route_tables[0]["Associations"]) == 2

    # Filter by route table ID
    route_table2_route_tables = client.describe_route_tables(
        Filters=[{"Name": "association.route-table-id", "Values": [route_table2.id]}]
    )["RouteTables"]
    assert len(route_table2_route_tables) == 1
    assert route_table2_route_tables[0]["RouteTableId"] == route_table2.id
    assert len(route_table2_route_tables[0]["Associations"]) == 1

    # Filter by subnet ID
    subnet_route_tables = client.describe_route_tables(
        Filters=[{"Name": "association.subnet-id", "Values": [subnet1.id]}]
    )["RouteTables"]
    assert len(subnet_route_tables) == 1
    assert subnet_route_tables[0]["RouteTableId"] == route_table1.id
    assert len(subnet_route_tables[0]["Associations"]) == 2


@mock_ec2
def test_route_tables_filters_vpc_peering_connection():
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
    assert len(new_routes) == 1

    new_route = new_routes[0]
    assert new_route.gateway_id is None
    assert new_route.instance_id is None
    assert new_route.vpc_peering_connection_id == vpc_pcx.id
    assert new_route.state == "active"
    assert new_route.destination_cidr_block == ROUTE_CIDR

    # Filter by Peering Connection
    route_tables = client.describe_route_tables(
        Filters=[{"Name": "route.vpc-peering-connection-id", "Values": [vpc_pcx.id]}]
    )["RouteTables"]
    assert len(route_tables) == 1
    route_table = route_tables[0]
    assert route_table["RouteTableId"] == main_route_table_id
    vpc_pcx_ids = [
        route["VpcPeeringConnectionId"]
        for route in route_table["Routes"]
        if "VpcPeeringConnectionId" in route
    ]
    all(vpc_pcx_id == vpc_pcx.id for vpc_pcx_id in vpc_pcx_ids)


@mock_ec2
def test_route_table_associations():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock="10.0.0.0/18")
    route_table = ec2.create_route_table(VpcId=vpc.id)

    # Refresh
    r = client.describe_route_tables(RouteTableIds=[route_table.id])["RouteTables"][0]
    assert len(r["Associations"]) == 0

    # Associate
    association_id = client.associate_route_table(
        RouteTableId=route_table.id, SubnetId=subnet.id
    )["AssociationId"]

    # Refresh
    r = client.describe_route_tables(RouteTableIds=[route_table.id])["RouteTables"][0]
    assert len(r["Associations"]) == 1

    assert r["Associations"][0]["RouteTableAssociationId"] == association_id
    assert r["Associations"][0]["Main"] is False
    assert r["Associations"][0]["RouteTableId"] == route_table.id
    assert r["Associations"][0]["SubnetId"] == subnet.id

    # Associate is idempotent
    association_id_idempotent = client.associate_route_table(
        RouteTableId=route_table.id, SubnetId=subnet.id
    )["AssociationId"]
    assert association_id_idempotent == association_id

    # Error: Attempt delete associated route table.
    with pytest.raises(ClientError) as ex:
        client.delete_route_table(RouteTableId=route_table.id)
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "DependencyViolation"

    # Disassociate
    client.disassociate_route_table(AssociationId=association_id)

    # Validate
    r = client.describe_route_tables(RouteTableIds=[route_table.id])["RouteTables"][0]
    assert len(r["Associations"]) == 0

    # Error: Disassociate with invalid association ID
    with pytest.raises(ClientError) as ex:
        client.disassociate_route_table(AssociationId=association_id)
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "InvalidAssociationID.NotFound"

    # Error: Associate with invalid subnet ID
    with pytest.raises(ClientError) as ex:
        client.associate_route_table(
            RouteTableId=route_table.id, SubnetId="subnet-1234abcd"
        )
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "InvalidSubnetID.NotFound"

    # Error: Associate with invalid route table ID
    with pytest.raises(ClientError) as ex:
        client.associate_route_table(RouteTableId="rtb-1234abcd", SubnetId=subnet.id)
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "InvalidRouteTableID.NotFound"


@mock_ec2
def test_route_table_replace_route_table_association():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock="10.0.0.0/18")
    route_table1_id = ec2.create_route_table(VpcId=vpc.id).id
    route_table2_id = ec2.create_route_table(VpcId=vpc.id).id

    all_route_tables = client.describe_route_tables()["RouteTables"]
    all_ids = [rt["RouteTableId"] for rt in all_route_tables]
    assert route_table1_id in all_ids
    assert route_table2_id in all_ids

    # Refresh
    route_table1 = client.describe_route_tables(RouteTableIds=[route_table1_id])[
        "RouteTables"
    ][0]
    assert len(route_table1["Associations"]) == 0

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
    assert len(route_table1["Associations"]) == 1
    assert len(route_table2["Associations"]) == 0

    assert route_table1["Associations"][0]["RouteTableAssociationId"] == association_id1
    assert route_table1["Associations"][0]["Main"] is False
    assert route_table1["Associations"][0]["RouteTableId"] == route_table1_id
    assert route_table1["Associations"][0]["SubnetId"] == subnet.id

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
    assert len(route_table1["Associations"]) == 0
    assert len(route_table2["Associations"]) == 1

    assert route_table2["Associations"][0]["RouteTableAssociationId"] == association_id2
    assert route_table2["Associations"][0]["Main"] is False
    assert route_table2["Associations"][0]["RouteTableId"] == route_table2_id
    assert route_table2["Associations"][0]["SubnetId"] == subnet.id

    # Replace Association is idempotent
    association_id_idempotent = client.replace_route_table_association(
        AssociationId=association_id2, RouteTableId=route_table2_id
    )["NewAssociationId"]
    assert association_id_idempotent == association_id2

    # Error: Replace association with invalid association ID
    with pytest.raises(ClientError) as ex:
        client.replace_route_table_association(
            AssociationId="rtbassoc-1234abcd", RouteTableId=route_table1_id
        )
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "InvalidAssociationID.NotFound"

    # Error: Replace association with invalid route table ID
    with pytest.raises(ClientError) as ex:
        client.replace_route_table_association(
            AssociationId=association_id2, RouteTableId="rtb-1234abcd"
        )
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "InvalidRouteTableID.NotFound"


@mock_ec2
def test_route_table_replace_route_table_association_for_main():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    new_route_table_id = ec2.create_route_table(VpcId=vpc.id).id

    # Get main route table details
    main_route_table = client.describe_route_tables(
        Filters=[
            {"Name": "vpc-id", "Values": [vpc.id]},
            {"Name": "association.main", "Values": ["true"]},
        ]
    )["RouteTables"][0]
    main_route_table_id = main_route_table["RouteTableId"]
    main_route_table_association_id = main_route_table["Associations"][0][
        "RouteTableAssociationId"
    ]

    # Replace Association
    new_association = client.replace_route_table_association(
        AssociationId=main_route_table_association_id, RouteTableId=new_route_table_id
    )
    new_association_id = new_association["NewAssociationId"]

    # Validate the format
    assert new_association["AssociationState"]["State"] == "associated"

    # Refresh
    main_route_table = client.describe_route_tables(
        RouteTableIds=[main_route_table_id]
    )["RouteTables"][0]
    new_route_table = client.describe_route_tables(RouteTableIds=[new_route_table_id])[
        "RouteTables"
    ][0]

    # Validate
    assert len(main_route_table["Associations"]) == 0
    assert len(new_route_table["Associations"]) == 1
    assert (
        new_route_table["Associations"][0]["RouteTableAssociationId"]
        == new_association_id
    )
    assert new_route_table["Associations"][0]["Main"] is True


@mock_ec2
def test_route_table_get_by_tag():
    ec2 = boto3.resource("ec2", region_name="eu-central-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")

    route_table = ec2.create_route_table(VpcId=vpc.id)
    tag_value = str(uuid4())
    route_table.create_tags(Tags=[{"Key": "Name", "Value": tag_value}])

    filters = [{"Name": "tag:Name", "Values": [tag_value]}]
    route_tables = list(ec2.route_tables.filter(Filters=filters))

    assert len(route_tables) == 1
    assert route_tables[0].vpc_id == vpc.id
    assert route_tables[0].id == route_table.id
    assert len(route_tables[0].tags) == 1
    assert route_tables[0].tags[0] == {"Key": "Name", "Value": tag_value}


@mock_ec2
def test_routes_additional():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    main_route_table_id = client.describe_route_tables(
        Filters=[{"Name": "vpc-id", "Values": [vpc.id]}]
    )["RouteTables"][0]["RouteTableId"]
    main_route_table = ec2.RouteTable(main_route_table_id)

    assert len(main_route_table.routes) == 1
    igw = ec2.create_internet_gateway()
    ROUTE_CIDR = "10.0.0.4/24"

    main_route_table.create_route(DestinationCidrBlock=ROUTE_CIDR, GatewayId=igw.id)

    assert len(main_route_table.routes) == 2
    new_routes = [
        route
        for route in main_route_table.routes
        if route.destination_cidr_block != vpc.cidr_block
    ]
    assert len(new_routes) == 1

    new_route = new_routes[0]
    assert new_route.gateway_id == igw.id
    assert new_route.instance_id is None
    assert new_route.state == "active"
    assert new_route.destination_cidr_block == ROUTE_CIDR

    client.delete_route(
        RouteTableId=main_route_table.id, DestinationCidrBlock=ROUTE_CIDR
    )

    main_route_table.reload()

    assert len(main_route_table.routes) == 1
    new_routes = [
        route
        for route in main_route_table.routes
        if route.destination_cidr_block != vpc.cidr_block
    ]
    assert len(new_routes) == 0

    with pytest.raises(ClientError) as ex:
        client.delete_route(
            RouteTableId=main_route_table.id, DestinationCidrBlock=ROUTE_CIDR
        )
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "InvalidRoute.NotFound"


@mock_ec2
def test_routes_replace():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock="10.0.0.0/24")

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

    eni = ec2.create_network_interface(SubnetId=subnet.id)

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
        assert len(routes) == 1
        return routes[0]

    client.replace_route(
        RouteTableId=main_route_table.id,
        DestinationCidrBlock=ROUTE_CIDR,
        InstanceId=instance.id,
    )

    target_route = get_target_route()
    assert "GatewayId" not in target_route
    assert target_route["InstanceId"] == instance.id
    assert "NetworkInterfaceId" not in target_route
    assert target_route["State"] == "active"
    assert target_route["DestinationCidrBlock"] == ROUTE_CIDR

    client.replace_route(
        RouteTableId=main_route_table.id,
        DestinationCidrBlock=ROUTE_CIDR,
        GatewayId=igw.id,
    )

    target_route = get_target_route()
    assert target_route["GatewayId"] == igw.id
    assert "InstanceId" not in target_route
    assert "NetworkInterfaceId" not in target_route
    assert target_route["State"] == "active"
    assert target_route["DestinationCidrBlock"] == ROUTE_CIDR

    client.replace_route(
        RouteTableId=main_route_table.id,
        DestinationCidrBlock=ROUTE_CIDR,
        NetworkInterfaceId=eni.id,
    )

    target_route = get_target_route()
    assert "GatewayId" not in target_route
    assert "InstanceId" not in target_route
    assert target_route["NetworkInterfaceId"] == eni.id
    assert target_route["State"] == "active"
    assert target_route["DestinationCidrBlock"] == ROUTE_CIDR

    with pytest.raises(ClientError) as ex:
        client.replace_route(
            RouteTableId="rtb-1234abcd",
            DestinationCidrBlock=ROUTE_CIDR,
            GatewayId=igw.id,
        )
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "InvalidRouteTableID.NotFound"

    with pytest.raises(ClientError) as ex:
        client.replace_route(
            RouteTableId=main_route_table.id,
            DestinationCidrBlock="1.1.1.1/32",
            NetworkInterfaceId=eni.id,
        )
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    # This should be 'InvalidRoute.NotFound' in line with the delete_route()
    # equivalent, but for some reason AWS returns InvalidParameterValue instead.
    assert ex.value.response["Error"]["Code"] == "InvalidParameterValue"


@mock_ec2
def test_routes_already_exist():
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
    ROUTE_CIDR = "10.0.0.0/23"
    ROUTE_SUB_CIDR = "10.0.0.0/24"
    ROUTE_NO_CONFLICT_CIDR = "10.0.2.0/24"

    # Various route targets
    igw = ec2.create_internet_gateway()

    # Create initial route
    main_route_table.create_route(DestinationCidrBlock=ROUTE_CIDR, GatewayId=igw.id)
    main_route_table.create_route(
        DestinationCidrBlock=ROUTE_NO_CONFLICT_CIDR, GatewayId=igw.id
    )

    # Create
    with pytest.raises(ClientError) as ex:
        client.create_route(
            RouteTableId=main_route_table.id,
            DestinationCidrBlock=ROUTE_CIDR,
            GatewayId=igw.id,
        )

    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "RouteAlreadyExists"

    # We can create a sub cidr
    client.create_route(
        RouteTableId=main_route_table.id,
        DestinationCidrBlock=ROUTE_SUB_CIDR,
        GatewayId=igw.id,
    )
    # Or even a catch-all
    client.create_route(
        RouteTableId=main_route_table.id,
        DestinationCidrBlock="0.0.0.0/0",
        GatewayId=igw.id,
    )


@mock_ec2
def test_routes_not_supported():
    client = boto3.client("ec2", region_name="us-east-1")
    main_route_table_id = client.describe_route_tables()["RouteTables"][0][
        "RouteTableId"
    ]

    ROUTE_CIDR = "10.0.0.4/24"

    # Create
    with pytest.raises(ClientError) as ex:
        client.create_route(
            RouteTableId=main_route_table_id,
            DestinationCidrBlock=ROUTE_CIDR,
            NetworkInterfaceId="eni-1234abcd",
        )
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "InvalidNetworkInterfaceID.NotFound"


@mock_ec2
def test_routes_vpc_peering_connection():
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
    assert len(new_routes) == 1

    new_route = new_routes[0]
    assert new_route.gateway_id is None
    assert new_route.instance_id is None
    assert new_route.vpc_peering_connection_id == vpc_pcx.id
    assert new_route.state == "active"
    assert new_route.destination_cidr_block == ROUTE_CIDR


@mock_ec2
def test_routes_vpn_gateway():
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
    assert len(new_routes) == 1

    new_route = new_routes[0]
    assert new_route.gateway_id == vpn_gw_id
    assert new_route.instance_id is None
    assert new_route.vpc_peering_connection_id is None


@mock_ec2
def test_network_acl_tagging():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")

    route_table = ec2.create_route_table(VpcId=vpc.id)
    route_table.create_tags(Tags=[{"Key": "a key", "Value": "some value"}])

    tag = client.describe_tags(
        Filters=[{"Name": "resource-id", "Values": [route_table.id]}]
    )["Tags"][0]
    assert tag["ResourceType"] == "route-table"
    assert tag["Key"] == "a key"
    assert tag["Value"] == "some value"

    all_route_tables = client.describe_route_tables()["RouteTables"]
    test_route_table = next(
        na for na in all_route_tables if na["RouteTableId"] == route_table.id
    )
    assert test_route_table["Tags"] == [{"Value": "some value", "Key": "a key"}]


@mock_ec2
def test_create_route_with_invalid_destination_cidr_block_parameter():
    ec2 = boto3.resource("ec2", region_name="us-west-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    vpc.reload()
    assert vpc.is_default is False

    route_table = ec2.create_route_table(VpcId=vpc.id)
    route_table.reload()

    internet_gateway = ec2.create_internet_gateway()
    vpc.attach_internet_gateway(InternetGatewayId=internet_gateway.id)
    internet_gateway.reload()

    destination_cidr_block = "1000.1.0.0/20"
    with pytest.raises(ClientError) as ex:
        route_table.create_route(
            DestinationCidrBlock=destination_cidr_block, GatewayId=internet_gateway.id
        )
    assert (
        str(ex.value)
        == f"An error occurred (InvalidParameterValue) when calling the CreateRoute operation: Value ({destination_cidr_block}) for parameter destinationCidrBlock is invalid. This is not a valid CIDR block."
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
    assert len(new_routes) == 1
    assert new_routes[0].route_table_id is not None


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

    assert route["ResponseMetadata"]["HTTPStatusCode"] == 200


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

    assert len(nat_gw_routes) == 1
    assert nat_gw_routes[0]["DestinationCidrBlock"] == "0.0.0.0/0"
    assert nat_gw_routes[0]["NatGatewayId"] == nat_gw_id
    assert nat_gw_routes[0]["State"] == "active"


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

    assert vpc_end_point["VpcEndpoint"]["ServiceName"] == "com.amazonaws.us-east-1.s3"
    assert (
        vpc_end_point["VpcEndpoint"]["RouteTableIds"][0]
        == route_table["RouteTable"]["RouteTableId"]
    )
    assert vpc_end_point["VpcEndpoint"]["VpcId"] == vpc["Vpc"]["VpcId"]
    assert len(vpc_end_point["VpcEndpoint"]["DnsEntries"]) == 0

    # test with any end point type as gateway
    vpc_end_point = ec2.create_vpc_endpoint(
        VpcId=vpc["Vpc"]["VpcId"],
        ServiceName="com.amazonaws.us-east-1.s3",
        RouteTableIds=[route_table["RouteTable"]["RouteTableId"]],
        VpcEndpointType="gateway",
    )

    assert vpc_end_point["VpcEndpoint"]["ServiceName"] == "com.amazonaws.us-east-1.s3"
    assert (
        vpc_end_point["VpcEndpoint"]["RouteTableIds"][0]
        == route_table["RouteTable"]["RouteTableId"]
    )
    assert vpc_end_point["VpcEndpoint"]["VpcId"] == vpc["Vpc"]["VpcId"]
    assert len(vpc_end_point["VpcEndpoint"]["DnsEntries"]) == 0

    # test with end point type as interface
    vpc_end_point = ec2.create_vpc_endpoint(
        VpcId=vpc["Vpc"]["VpcId"],
        ServiceName="com.amazonaws.us-east-1.s3",
        SubnetIds=[subnet["Subnet"]["SubnetId"]],
        VpcEndpointType="interface",
    )

    assert vpc_end_point["VpcEndpoint"]["ServiceName"] == "com.amazonaws.us-east-1.s3"
    assert vpc_end_point["VpcEndpoint"]["SubnetIds"][0] == subnet["Subnet"]["SubnetId"]
    assert vpc_end_point["VpcEndpoint"]["VpcId"] == vpc["Vpc"]["VpcId"]
    assert len(vpc_end_point["VpcEndpoint"]["DnsEntries"]) > 0


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

    assert len(route_table.tags) == 1


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
    assert eigw_route.get("EgressOnlyInternetGatewayId") == eigw_id
    assert eigw_route.get("State") == "active"


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
    assert err["Code"] == "InvalidGatewayID.NotFound"
    assert err["Message"] == "The eigw ID 'eoigw' does not exist"


@mock_ec2
def test_create_route_with_vpc_endpoint():
    # Setup
    _, ec2_client, route_table, vpc = setup_vpc()
    dest_cidr = "0.0.0.0/0"
    vpc_end_point = ec2_client.create_vpc_endpoint(
        VpcId=vpc.id,
        ServiceName="com.amazonaws.vpce.eu-central-1.vpce-svc-084fa044c50cb1290",
        RouteTableIds=[route_table.id],
        VpcEndpointType="GatewayLoadBalancer",
    )
    vpce_id = vpc_end_point["VpcEndpoint"]["VpcEndpointId"]

    # Execute
    ec2_client.create_route(
        DestinationCidrBlock=dest_cidr,
        VpcEndpointId=vpce_id,
        RouteTableId=route_table.id,
    )
    rt = ec2_client.describe_route_tables()
    new_route = rt["RouteTables"][-1]["Routes"][1]

    # Verify
    assert new_route["DestinationCidrBlock"] == dest_cidr
    assert new_route["GatewayId"] == vpce_id


@mock_ec2
def test_create_route_with_invalid_vpc_endpoint():
    # Setup
    _, ec2_client, route_table, vpc = setup_vpc()
    dest_cidr = "0.0.0.0/0"
    vpc_end_point = ec2_client.create_vpc_endpoint(
        VpcId=vpc.id,
        ServiceName="com.amazonaws.us-east-1.s3",
        RouteTableIds=[route_table.id],
        VpcEndpointType="Gateway",
    )
    vpce_id = vpc_end_point["VpcEndpoint"]["VpcEndpointId"]

    # Execute
    with pytest.raises(ClientError) as ex:
        ec2_client.create_route(
            DestinationCidrBlock=dest_cidr,
            VpcEndpointId=vpce_id,
            RouteTableId=route_table.id,
        )
    # Verify
    err = ex.value.response["Error"]
    assert err["Code"] == "RouteNotSupported"
    assert (
        err["Message"] == f"Route table contains unsupported route target: {vpce_id}. "
        "VPC Endpoints of this type cannot be used as route targets."
    )


@mock_ec2
def test_associate_route_table_by_gateway():
    ec2 = boto3.client("ec2", region_name="us-west-1")
    vpc_id = ec2.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]["VpcId"]
    route_table_id = ec2.create_route_table(VpcId=vpc_id)["RouteTable"]["RouteTableId"]
    igw_id = ec2.create_internet_gateway()["InternetGateway"]["InternetGatewayId"]
    assoc_id = ec2.associate_route_table(RouteTableId=route_table_id, GatewayId=igw_id)[
        "AssociationId"
    ]
    verify = ec2.describe_route_tables(
        Filters=[
            {"Name": "association.route-table-association-id", "Values": [assoc_id]}
        ]
    )["RouteTables"]

    assert len(verify[0]["Associations"]) == 1

    assert verify[0]["Associations"][0]["Main"] is False
    assert verify[0]["Associations"][0]["GatewayId"] == igw_id
    assert verify[0]["Associations"][0]["RouteTableAssociationId"] == assoc_id
    assert "SubnetId" not in verify[0]["Associations"][0]


@mock_ec2
def test_associate_route_table_by_subnet():
    ec2 = boto3.client("ec2", region_name="us-west-1")
    vpc_id = ec2.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]["VpcId"]
    route_table_id = ec2.create_route_table(VpcId=vpc_id)["RouteTable"]["RouteTableId"]
    subnet_id = ec2.create_subnet(VpcId=vpc_id, CidrBlock="10.0.0.0/24")["Subnet"][
        "SubnetId"
    ]
    assoc_id = ec2.associate_route_table(
        RouteTableId=route_table_id, SubnetId=subnet_id
    )["AssociationId"]
    verify = ec2.describe_route_tables(
        Filters=[
            {"Name": "association.route-table-association-id", "Values": [assoc_id]}
        ]
    )["RouteTables"]

    assert len(verify[0]["Associations"]) == 1

    assert verify[0]["Associations"][0]["Main"] is False
    assert verify[0]["Associations"][0]["SubnetId"] == subnet_id
    assert verify[0]["Associations"][0]["RouteTableAssociationId"] == assoc_id
    assert "GatewayId" not in verify[0]["Associations"][0]


def setup_vpc():
    ec2_resource = boto3.resource("ec2", region_name="eu-central-1")
    ec2_client = boto3.client("ec2", region_name="eu-central-1")

    vpc = ec2_resource.create_vpc(CidrBlock="10.0.0.0/16")
    ec2_resource.create_subnet(
        VpcId=vpc.id, CidrBlock="10.0.0.0/24", AvailabilityZone="us-west-2a"
    )

    route_table = ec2_resource.create_route_table(VpcId=vpc.id)

    return ec2_resource, ec2_client, route_table, vpc
