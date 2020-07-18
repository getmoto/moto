from __future__ import unicode_literals
from moto.core.responses import BaseResponse
from moto.ec2.utils import filters_from_querystring


class RouteTables(BaseResponse):
    def associate_route_table(self):
        route_table_id = self._get_param("RouteTableId")
        subnet_id = self._get_param("SubnetId")
        association_id = self.ec2_backend.associate_route_table(
            route_table_id, subnet_id
        )
        template = self.response_template(ASSOCIATE_ROUTE_TABLE_RESPONSE)
        return template.render(association_id=association_id)

    def create_route(self):
        route_table_id = self._get_param("RouteTableId")
        destination_cidr_block = self._get_param("DestinationCidrBlock")
        destination_ipv6_cidr_block = self._get_param("DestinationIpv6CidrBlock")
        gateway_id = self._get_param("GatewayId")
        instance_id = self._get_param("InstanceId")
        nat_gateway_id = self._get_param("NatGatewayId")
        interface_id = self._get_param("NetworkInterfaceId")
        pcx_id = self._get_param("VpcPeeringConnectionId")

        self.ec2_backend.create_route(
            route_table_id,
            destination_cidr_block,
            destination_ipv6_cidr_block,
            gateway_id=gateway_id,
            instance_id=instance_id,
            nat_gateway_id=nat_gateway_id,
            interface_id=interface_id,
            vpc_peering_connection_id=pcx_id,
        )

        template = self.response_template(CREATE_ROUTE_RESPONSE)
        return template.render()

    def create_route_table(self):
        vpc_id = self._get_param("VpcId")
        route_table = self.ec2_backend.create_route_table(vpc_id)
        template = self.response_template(CREATE_ROUTE_TABLE_RESPONSE)
        return template.render(route_table=route_table)

    def delete_route(self):
        route_table_id = self._get_param("RouteTableId")
        destination_cidr_block = self._get_param("DestinationCidrBlock")
        self.ec2_backend.delete_route(route_table_id, destination_cidr_block)
        template = self.response_template(DELETE_ROUTE_RESPONSE)
        return template.render()

    def delete_route_table(self):
        route_table_id = self._get_param("RouteTableId")
        self.ec2_backend.delete_route_table(route_table_id)
        template = self.response_template(DELETE_ROUTE_TABLE_RESPONSE)
        return template.render()

    def describe_route_tables(self):
        route_table_ids = self._get_multi_param("RouteTableId")
        filters = filters_from_querystring(self.querystring)
        route_tables = self.ec2_backend.get_all_route_tables(route_table_ids, filters)
        template = self.response_template(DESCRIBE_ROUTE_TABLES_RESPONSE)
        return template.render(route_tables=route_tables)

    def disassociate_route_table(self):
        association_id = self._get_param("AssociationId")
        self.ec2_backend.disassociate_route_table(association_id)
        template = self.response_template(DISASSOCIATE_ROUTE_TABLE_RESPONSE)
        return template.render()

    def replace_route(self):
        route_table_id = self._get_param("RouteTableId")
        destination_cidr_block = self._get_param("DestinationCidrBlock")
        gateway_id = self._get_param("GatewayId")
        instance_id = self._get_param("InstanceId")
        interface_id = self._get_param("NetworkInterfaceId")
        pcx_id = self._get_param("VpcPeeringConnectionId")

        self.ec2_backend.replace_route(
            route_table_id,
            destination_cidr_block,
            gateway_id=gateway_id,
            instance_id=instance_id,
            interface_id=interface_id,
            vpc_peering_connection_id=pcx_id,
        )

        template = self.response_template(REPLACE_ROUTE_RESPONSE)
        return template.render()

    def replace_route_table_association(self):
        route_table_id = self._get_param("RouteTableId")
        association_id = self._get_param("AssociationId")
        new_association_id = self.ec2_backend.replace_route_table_association(
            association_id, route_table_id
        )
        template = self.response_template(REPLACE_ROUTE_TABLE_ASSOCIATION_RESPONSE)
        return template.render(association_id=new_association_id)


CREATE_ROUTE_RESPONSE = """
<CreateRouteResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
   <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
   <return>true</return>
</CreateRouteResponse>
"""

REPLACE_ROUTE_RESPONSE = """
<ReplaceRouteResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
   <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
   <return>true</return>
</ReplaceRouteResponse>
"""

CREATE_ROUTE_TABLE_RESPONSE = """
<CreateRouteTableResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
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
      <tagSet>
      {% for tag in route_table.get_tags() %}
        <item>
          <resourceId>{{ tag.resource_id }}</resourceId>
          <resourceType>{{ tag.resource_type }}</resourceType>
          <key>{{ tag.key }}</key>
          <value>{{ tag.value }}</value>
        </item>
      {% endfor %}
      </tagSet>
   </routeTable>
</CreateRouteTableResponse>
"""

DESCRIBE_ROUTE_TABLES_RESPONSE = """
<DescribeRouteTablesResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
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
                {% if route.gateway %}
                  <gatewayId>{{ route.gateway.id }}</gatewayId>
                  <origin>CreateRoute</origin>
                  <state>active</state>
                {% endif %}
                {% if route.instance %}
                  <instanceId>{{ route.instance.id }}</instanceId>
                  <origin>CreateRoute</origin>
                  <state>active</state>
                {% endif %}
                {% if route.vpc_pcx %}
                  <vpcPeeringConnectionId>{{ route.vpc_pcx.id }}</vpcPeeringConnectionId>
                  <origin>CreateRoute</origin>
                  <state>blackhole</state>
                {% endif %}
                {% if route.nat_gateway %}
                  <natGatewayId>{{ route.nat_gateway.id }}</natGatewayId>
                  <state>active</state>
                {% endif %}
              </item>
            {% endfor %}
          </routeSet>
          <associationSet>
            {% for association_id,subnet_id in route_table.associations.items() %}
              <item>
                <routeTableAssociationId>{{ association_id }}</routeTableAssociationId>
                <routeTableId>{{ route_table.id }}</routeTableId>
                <main>false</main>
                <subnetId>{{ subnet_id }}</subnetId>
              </item>
            {% endfor %}
          </associationSet>
         <tagSet>
          {% for tag in route_table.get_tags() %}
           <item>
             <resourceId>{{ tag.resource_id }}</resourceId>
             <resourceType>{{ tag.resource_type }}</resourceType>
             <key>{{ tag.key }}</key>
             <value>{{ tag.value }}</value>
           </item>
          {% endfor %}
         </tagSet>
       </item>
     {% endfor %}
   </routeTableSet>
</DescribeRouteTablesResponse>
"""

DELETE_ROUTE_RESPONSE = """
<DeleteRouteResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
   <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
   <return>true</return>
</DeleteRouteResponse>
"""

DELETE_ROUTE_TABLE_RESPONSE = """
<DeleteRouteTableResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
   <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
   <return>true</return>
</DeleteRouteTableResponse>
"""

ASSOCIATE_ROUTE_TABLE_RESPONSE = """
<AssociateRouteTableResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
   <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
   <associationId>{{ association_id }}</associationId>
</AssociateRouteTableResponse>
"""

DISASSOCIATE_ROUTE_TABLE_RESPONSE = """
<DisassociateRouteTableResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
   <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
   <return>true</return>
</DisassociateRouteTableResponse>
"""

REPLACE_ROUTE_TABLE_ASSOCIATION_RESPONSE = """
<ReplaceRouteTableAssociationResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
   <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
   <newAssociationId>{{ association_id }}</newAssociationId>
</ReplaceRouteTableAssociationResponse>
"""
