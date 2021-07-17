from __future__ import unicode_literals
from moto.core.responses import BaseResponse
from moto.ec2.utils import filters_from_querystring


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
        transit_gateway_route_tables = self.ec2_backend.get_all_transit_gateway_route_tables(filters)
        template = self.response_template(DESCRIBE_TRANSIT_GATEWAY_ROUTE_TABLE_RESPONSE)
        return template.render(transit_gateway_route_tables=transit_gateway_route_tables)

    def delete_transit_gateway_route_table(self):
        transit_gateway_route_table_id = self._get_param("TransitGatewayRouteTableId")
        transit_gateway_route_table = self.ec2_backend.delete_transit_gateway_route_table(transit_gateway_route_table_id)
        template = self.response_template(DELETE_TRANSIT_GATEWAY_ROUTE_TABLE_RESPONSE)
        return template.render(transit_gateway_route_table=transit_gateway_route_table)


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
