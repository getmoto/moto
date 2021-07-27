from __future__ import unicode_literals
from moto.core.responses import BaseResponse
from moto.ec2.utils import filters_from_querystring
from moto.utilities.utils import str2bool


class TransitGatewayRouteTable(BaseResponse):
    def create_transit_gateway_route_table(self):
        transit_gateway_id = self._get_param("TransitGatewayId")
        tags = self._get_multi_param("TagSpecifications")
        tags = tags[0] if isinstance(tags, list) and len(tags) == 1 else tags
        tags = (tags or {}).get("Tag", [])
        tags = {t["Key"]: t["Value"] for t in tags}

        transit_gateway_route_table = self.ec2_backend.create_transit_gateway_route_table(
            transit_gateway_id=transit_gateway_id, tags=tags
        )
        template = self.response_template(CREATE_TRANSIT_GATEWAY_ROUTE_TABLE_RESPONSE)
        return template.render(transit_gateway_route_table=transit_gateway_route_table)

    def describe_transit_gateway_route_tables(self):
        filters = filters_from_querystring(self.querystring)
        transit_gateway_ids = (
            self._get_multi_param("TransitGatewayRouteTableIds") or None
        )
        transit_gateway_route_tables = self.ec2_backend.get_all_transit_gateway_route_tables(
            transit_gateway_ids, filters
        )
        template = self.response_template(DESCRIBE_TRANSIT_GATEWAY_ROUTE_TABLE_RESPONSE)
        return template.render(
            transit_gateway_route_tables=transit_gateway_route_tables
        )

    def delete_transit_gateway_route_table(self):
        transit_gateway_route_table_id = self._get_param("TransitGatewayRouteTableId")
        transit_gateway_route_table = self.ec2_backend.delete_transit_gateway_route_table(
            transit_gateway_route_table_id
        )
        template = self.response_template(DELETE_TRANSIT_GATEWAY_ROUTE_TABLE_RESPONSE)
        return template.render(transit_gateway_route_table=transit_gateway_route_table)

    def create_transit_gateway_route(self):
        transit_gateway_attachment_id = self._get_param("TransitGatewayAttachmentId")
        destination_cidr_block = self._get_param("DestinationCidrBlock")
        transit_gateway_route_table_id = self._get_param("TransitGatewayRouteTableId")
        blackhole = str2bool(self._get_param("Blackhole"))
        transit_gateways_route_table = self.ec2_backend.create_transit_gateway_route(
            destination_cidr_block=destination_cidr_block,
            transit_gateway_route_table_id=transit_gateway_route_table_id,
            transit_gateway_attachment_id=transit_gateway_attachment_id,
            blackhole=blackhole,
        )
        template = self.response_template(CREATE_TRANSIT_GATEWAY_ROUTE_RESPONSE)
        return template.render(
            transit_gateway_route_table=transit_gateways_route_table,
            destination_cidr_block=destination_cidr_block,
        )

    def delete_transit_gateway_route(self):
        destination_cidr_block = self._get_param("DestinationCidrBlock")
        transit_gateway_route_table_id = self._get_param("TransitGatewayRouteTableId")
        transit_gateway_route_table = self.ec2_backend.delete_transit_gateway_route(
            destination_cidr_block=destination_cidr_block,
            transit_gateway_route_table_id=transit_gateway_route_table_id,
        )
        template = self.response_template(DELETE_TRANSIT_GATEWAY_ROUTE_RESPONSE)
        rendered_template = template.render(
            transit_gateway_route_table=transit_gateway_route_table,
            destination_cidr_block=destination_cidr_block,
        )
        del transit_gateway_route_table.routes[destination_cidr_block]
        return rendered_template

    def search_transit_gateway_routes(self):
        transit_gateway_route_table_id = self._get_param("TransitGatewayRouteTableId")
        filters = filters_from_querystring(self.querystring)
        max_results = self._get_param("MaxResults")
        transit_gateway_routes = self.ec2_backend.search_transit_gateway_routes(
            transit_gateway_route_table_id=transit_gateway_route_table_id,
            filters=filters,
            max_results=max_results,
        )
        template = self.response_template(SEARCH_TRANSIT_GATEWAY_ROUTES_RESPONSE)
        return template.render(transit_gateway_routes=transit_gateway_routes)


CREATE_TRANSIT_GATEWAY_ROUTE_TABLE_RESPONSE = """<CreateTransitGatewayRouteTableResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">
    <requestId>3a495d25-08d4-466d-822e-477c9b1fc606</requestId>
    <transitGatewayRouteTable>
        <creationTime>{{ transit_gateway_route_table.create_time }}</creationTime>
        <defaultAssociationRouteTable>{{ transit_gateway_route_table.default_association_route_table }}</defaultAssociationRouteTable>
        <defaultPropagationRouteTable>{{ transit_gateway_route_table.default_propagation_route_table }}</defaultPropagationRouteTable>
        <state>{{ transit_gateway_route_table.state }}</state>
        <transitGatewayId>{{ transit_gateway_route_table.transit_gateway_id }}</transitGatewayId>
        <transitGatewayRouteTableId>{{ transit_gateway_route_table.id }}</transitGatewayRouteTableId>
        <tagSet>
            {% for tag in transit_gateway_route_table.get_tags() %}
                <item>
                    <key>{{ tag.key }}</key>
                    <value>{{ tag.value }}</value>
                </item>
            {% endfor %}
        </tagSet>
    </transitGatewayRouteTable>
</CreateTransitGatewayRouteTableResponse>
"""

DESCRIBE_TRANSIT_GATEWAY_ROUTE_TABLE_RESPONSE = """<DescribeTransitGatewayRouteTablesResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">
    <requestId>f9dea58a-7bb3-458b-a40d-0b7ae32eefdb</requestId>
    <transitGatewayRouteTables>
        {% for transit_gateway_route_table in transit_gateway_route_tables %}
        <item>
            <creationTime>{{ transit_gateway_route_table.create_time }}</creationTime>
            <defaultAssociationRouteTable>{{ transit_gateway_route_table.default_association_route_table }}</defaultAssociationRouteTable>
            <defaultPropagationRouteTable>{{ transit_gateway_route_table.default_propagation_route_table }}</defaultPropagationRouteTable>
            <state>{{ transit_gateway_route_table.state }}</state>
            <tagSet>
                {% for tag in transit_gateway_route_table.get_tags() %}
                    <item>
                        <key>{{ tag.key }}</key>
                        <value>{{ tag.value }}</value>
                    </item>
                {% endfor %}
            </tagSet>
            <transitGatewayId>{{ transit_gateway_route_table.transit_gateway_id }}</transitGatewayId>
            <transitGatewayRouteTableId>{{ transit_gateway_route_table.id }}</transitGatewayRouteTableId>
        </item>
        {% endfor %}
    </transitGatewayRouteTables>
</DescribeTransitGatewayRouteTablesResponse>
"""

DELETE_TRANSIT_GATEWAY_ROUTE_TABLE_RESPONSE = """<DeleteTransitGatewayRouteTableResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">
    <requestId>a9a07226-c7b1-4305-9934-0bcfc3ef1c5e</requestId>
    <transitGatewayRouteTable>
        {% for transit_gateway_route_table in transit_gateway_route_tables %}
        <item>
            <creationTime>{{ transit_gateway_route_table.create_time }}</creationTime>
            <defaultAssociationRouteTable>{{ transit_gateway_route_table.default_association_route_table }}</defaultAssociationRouteTable>
            <defaultPropagationRouteTable>{{ transit_gateway_route_table.default_propagation_route_table }}</defaultPropagationRouteTable>
            <state>{{ transit_gateway_route_table.state }}</state>
            <transitGatewayId>{{ transit_gateway_route_table.transit_gateway_id }}</transitGatewayId>
            <transitGatewayRouteTableId>{{ transit_gateway_route_table.id }}</transitGatewayRouteTableId>
        </item>
        {% endfor %}
    </transitGatewayRouteTable>
</DeleteTransitGatewayRouteTableResponse>
"""


CREATE_TRANSIT_GATEWAY_ROUTE_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<CreateTransitGatewayRouteResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">
    <requestId>072b02ce-df3a-4de6-a20b-6653ae4b91a4</requestId>
    <route>
        <destinationCidrBlock>{{ transit_gateway_route_table.routes[destination_cidr_block]['destinationCidrBlock'] }}</destinationCidrBlock>
        <state>{{ transit_gateway_route_table.routes[destination_cidr_block]['state'] }}</state>
        <type>{{ transit_gateway_route_table.routes[destination_cidr_block]['type'] }}</type>
    </route>
</CreateTransitGatewayRouteResponse>
"""

DELETE_TRANSIT_GATEWAY_ROUTE_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<DeleteTransitGatewayRouteResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">
    <requestId>2109d5bb-f874-4f35-b419-4723792a638f</requestId>
    <route>
        <destinationCidrBlock>{{ transit_gateway_route_table.routes[destination_cidr_block]['destinationCidrBlock'] }}</destinationCidrBlock>
        <state>{{ transit_gateway_route_table.routes[destination_cidr_block]['state'] }}</state>
        <type>{{ transit_gateway_route_table.routes[destination_cidr_block]['type'] }}</type>
    </route>
</DeleteTransitGatewayRouteResponse>
"""

SEARCH_TRANSIT_GATEWAY_ROUTES_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<SearchTransitGatewayRoutesResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">
    <requestId>04b46ad2-5a0e-46db-afe4-68679a193b48</requestId>
    <routeSet>
        {% for route in transit_gateway_routes %}
        <item>
            <destinationCidrBlock>{{ route['destinationCidrBlock'] }}</destinationCidrBlock>
            <state>{{ route['state'] }}</state>
            <type>{{ route['type'] }}</type>
        </item>
        {% endfor %}
    </routeSet>
    <additionalRoutesAvailable>false</additionalRoutesAvailable>
</SearchTransitGatewayRoutesResponse>
"""
