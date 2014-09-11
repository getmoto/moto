from __future__ import unicode_literals
from jinja2 import Template

from moto.core.responses import BaseResponse
from moto.ec2.models import ec2_backend
from moto.ec2.utils import route_table_ids_from_querystring, filters_from_querystring, optional_from_querystring


class RouteTables(BaseResponse):
    def associate_route_table(self):
        raise NotImplementedError('RouteTables(AmazonVPC).associate_route_table is not yet implemented')

    def create_route(self):
        route_table_id = self.querystring.get('RouteTableId')[0]
        destination_cidr_block = self.querystring.get('DestinationCidrBlock')[0]

        internet_gateway_id = optional_from_querystring('GatewayId', self.querystring)
        instance_id = optional_from_querystring('InstanceId', self.querystring)
        interface_id = optional_from_querystring('NetworkInterfaceId', self.querystring)
        pcx_id = optional_from_querystring('VpcPeeringConnectionId', self.querystring)

        ec2_backend.create_route(
            route_table_id,
            destination_cidr_block,
            gateway_id=internet_gateway_id,
            instance_id=instance_id,
            interface_id=interface_id,
            vpc_peering_connection_id=pcx_id,
        )

        template = Template(CREATE_ROUTE_RESPONSE)
        return template.render()

    def create_route_table(self):
        vpc_id = self.querystring.get('VpcId')[0]
        route_table = ec2_backend.create_route_table(vpc_id)
        template = Template(CREATE_ROUTE_TABLE_RESPONSE)
        return template.render(route_table=route_table)

    def delete_route(self):
        route_table_id = self.querystring.get('RouteTableId')[0]
        destination_cidr_block = self.querystring.get('DestinationCidrBlock')[0]
        ec2_backend.delete_route(route_table_id, destination_cidr_block)
        template = Template(DELETE_ROUTE_RESPONSE)
        return template.render()

    def delete_route_table(self):
        route_table_id = self.querystring.get('RouteTableId')[0]
        ec2_backend.delete_route_table(route_table_id)
        template = Template(DELETE_ROUTE_TABLE_RESPONSE)
        return template.render()

    def describe_route_tables(self):
        route_table_ids = route_table_ids_from_querystring(self.querystring)
        filters = filters_from_querystring(self.querystring)
        route_tables = ec2_backend.get_all_route_tables(route_table_ids, filters)
        template = Template(DESCRIBE_ROUTE_TABLES_RESPONSE)
        return template.render(route_tables=route_tables)

    def disassociate_route_table(self):
        raise NotImplementedError('RouteTables(AmazonVPC).disassociate_route_table is not yet implemented')

    def replace_route(self):
        route_table_id = self.querystring.get('RouteTableId')[0]
        destination_cidr_block = self.querystring.get('DestinationCidrBlock')[0]

        internet_gateway_id = optional_from_querystring('GatewayId', self.querystring)
        instance_id = optional_from_querystring('InstanceId', self.querystring)
        interface_id = optional_from_querystring('NetworkInterfaceId', self.querystring)
        pcx_id = optional_from_querystring('VpcPeeringConnectionId', self.querystring)

        ec2_backend.replace_route(
            route_table_id,
            destination_cidr_block,
            gateway_id=internet_gateway_id,
            instance_id=instance_id,
            interface_id=interface_id,
            vpc_peering_connection_id=pcx_id,
        )

        template = Template(REPLACE_ROUTE_RESPONSE)
        return template.render()

    def replace_route_table_association(self):
        raise NotImplementedError('RouteTables(AmazonVPC).replace_route_table_association is not yet implemented')


CREATE_ROUTE_RESPONSE = """
<CreateRouteResponse xmlns="http://ec2.amazonaws.com/doc/2013-07-15/">
   <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
   <return>true</return>
</CreateRouteResponse>
"""

REPLACE_ROUTE_RESPONSE = """
<ReplaceRouteResponse xmlns="http://ec2.amazonaws.com/doc/2013-07-15/">
   <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
   <return>true</return>
</ReplaceRouteResponse>
"""

CREATE_ROUTE_TABLE_RESPONSE = """
<CreateRouteTableResponse xmlns="http://ec2.amazonaws.com/doc/2013-07-15/">
   <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
   <routeTable>
      <routeTableId>{{ route_table.id }}</routeTableId>
      <vpcId>{{ route_table.vpc_id }}</vpcId>
      <routeSet>
         {% for route in route_table.routes.values() %}
           {% if route.local %}
           <item>
             <destinationCidrBlock>{{ route.destination_cidr_block }}</destinationCidrBlock>
             <gatewayId>local</gatewayId>
             <state>active</state>
           </item>
           {% endif %}
         {% endfor %}
      </routeSet>
      <associationSet/>
      <tagSet/>
   </routeTable>
</CreateRouteTableResponse>
"""

DESCRIBE_ROUTE_TABLES_RESPONSE = """
<DescribeRouteTablesResponse xmlns="http://ec2.amazonaws.com/doc/2013-08-15/">
   <requestId>6f570b0b-9c18-4b07-bdec-73740dcf861a</requestId>
   <routeTableSet>
     {% for route_table in route_tables %}
       <item>
          <routeTableId>{{ route_table.id }}</routeTableId>
          <vpcId>{{ route_table.vpc_id }}</vpcId>
          <routeSet>
            {% for route in route_table.routes.values() %}
              <item>
                <destinationCidrBlock>{{ route.destination_cidr_block }}</destinationCidrBlock>
                {% if route.local %}
                  <gatewayId>local</gatewayId>
                  <origin>CreateRouteTable</origin>
                  <state>active</state>
                {% endif %}
                {% if route.internet_gateway %}
                  <gatewayId>{{ route.internet_gateway.id }}</gatewayId>
                  <origin>CreateRoute</origin>
                  <state>active</state>
                {% endif %}
                {% if route.instance %}
                  <instanceId>{{ route.instance.id }}</instanceId>
                  <origin>CreateRoute</origin>
                  <state>active</state>
                {% endif %}
                {% if route.vpc_pcx %}
                  <origin>CreateRoute</origin>
                  <state>blackhole</state>
                {% endif %}
              </item>
            {% endfor %}
          </routeSet>
          <associationSet>
            {% if route_table.association_id %}
              <item>
                  <routeTableAssociationId>{{ route_table.association_id }}</routeTableAssociationId>
                  <routeTableId>{{ route_table.id }}</routeTableId>
                {% if not route_table.subnet_id %}
                  <main>true</main>
                {% endif %}
                {% if route_table.subnet_id %}
                  <subnetId>{{ route_table.subnet_id }}</subnetId>
                {% endif %}
              </item>
            {% endif %}
          </associationSet>
         <tagSet/>
       </item>
     {% endfor %}
   </routeTableSet>
</DescribeRouteTablesResponse>
"""

DELETE_ROUTE_RESPONSE = """
<DeleteRouteResponse xmlns="http://ec2.amazonaws.com/doc/2013-07-15/">
   <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
   <return>true</return>
</DeleteRouteResponse>
"""

DELETE_ROUTE_TABLE_RESPONSE = """
<DeleteRouteTableResponse xmlns="http://ec2.amazonaws.com/doc/2013-07-15/">
   <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
   <return>true</return>
</DeleteRouteTableResponse>
"""
