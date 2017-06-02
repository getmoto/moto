from __future__ import unicode_literals
import random
from moto.core.responses import BaseResponse
from moto.ec2.utils import filters_from_querystring


class Subnets(BaseResponse):

    def create_subnet(self):
        vpc_id = self.querystring.get('VpcId')[0]
        cidr_block = self.querystring.get('CidrBlock')[0]
        if 'AvailabilityZone' in self.querystring:
            availability_zone = self.querystring['AvailabilityZone'][0]
        else:
            zone = random.choice(
                self.ec2_backend.describe_availability_zones())
            availability_zone = zone.name
        subnet = self.ec2_backend.create_subnet(
            vpc_id,
            cidr_block,
            availability_zone,
        )
        template = self.response_template(CREATE_SUBNET_RESPONSE)
        return template.render(subnet=subnet)

    def delete_subnet(self):
        subnet_id = self.querystring.get('SubnetId')[0]
        subnet = self.ec2_backend.delete_subnet(subnet_id)
        template = self.response_template(DELETE_SUBNET_RESPONSE)
        return template.render(subnet=subnet)

    def describe_subnets(self):
        filters = filters_from_querystring(self.querystring)

        subnet_ids = []
        idx = 1
        key = 'SubnetId.{0}'.format(idx)
        while key in self.querystring:
            v = self.querystring[key]
            subnet_ids.append(v[0])
            idx += 1
            key = 'SubnetId.{0}'.format(idx)

        subnets = self.ec2_backend.get_all_subnets(subnet_ids, filters)
        template = self.response_template(DESCRIBE_SUBNETS_RESPONSE)
        return template.render(subnets=subnets)

    def modify_subnet_attribute(self):
        subnet_id = self.querystring.get('SubnetId')[0]
        map_public_ip = self.querystring.get('MapPublicIpOnLaunch.Value')[0]
        self.ec2_backend.modify_subnet_attribute(subnet_id, map_public_ip)
        return MODIFY_SUBNET_ATTRIBUTE_RESPONSE


CREATE_SUBNET_RESPONSE = """
<CreateSubnetResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
  <subnet>
    <subnetId>{{ subnet.id }}</subnetId>
    <state>pending</state>
    <vpcId>{{ subnet.vpc_id }}</vpcId>
    <cidrBlock>{{ subnet.cidr_block }}</cidrBlock>
    <availableIpAddressCount>251</availableIpAddressCount>
    <availabilityZone>{{ subnet.availability_zone }}</availabilityZone>
    <tagSet>
      {% for tag in subnet.get_tags() %}
        <item>
          <resourceId>{{ tag.resource_id }}</resourceId>
          <resourceType>{{ tag.resource_type }}</resourceType>
          <key>{{ tag.key }}</key>
          <value>{{ tag.value }}</value>
        </item>
      {% endfor %}
    </tagSet>
  </subnet>
</CreateSubnetResponse>"""

DELETE_SUBNET_RESPONSE = """
<DeleteSubnetResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
   <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
   <return>true</return>
</DeleteSubnetResponse>"""

DESCRIBE_SUBNETS_RESPONSE = """
<DescribeSubnetsResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
  <subnetSet>
    {% for subnet in subnets %}
      <item>
        <subnetId>{{ subnet.id }}</subnetId>
        <state>available</state>
        <vpcId>{{ subnet.vpc_id }}</vpcId>
        <cidrBlock>{{ subnet.cidr_block }}</cidrBlock>
        <availableIpAddressCount>251</availableIpAddressCount>
        <availabilityZone>{{ subnet.availability_zone }}</availabilityZone>
        <defaultForAz>{{ subnet.default_for_az }}</defaultForAz>
        <mapPublicIpOnLaunch>{{ subnet.map_public_ip_on_launch }}</mapPublicIpOnLaunch>
        <tagSet>
          {% for tag in subnet.get_tags() %}
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
  </subnetSet>
</DescribeSubnetsResponse>"""

MODIFY_SUBNET_ATTRIBUTE_RESPONSE = """
<ModifySubnetAttributeResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
  <return>true</return>
</ModifySubnetAttributeResponse>"""
