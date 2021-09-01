from __future__ import unicode_literals
import random
from moto.core.responses import BaseResponse
from moto.core.utils import camelcase_to_underscores
from moto.ec2.utils import filters_from_querystring


class Subnets(BaseResponse):
    def create_subnet(self):
        vpc_id = self._get_param("VpcId")
        cidr_block = self._get_param("CidrBlock")
        ipv6_cidr_block = self._get_param("Ipv6CidrBlock")
        availability_zone = self._get_param("AvailabilityZone")
        availability_zone_id = self._get_param("AvailabilityZoneId")
        tags = self._get_multi_param("TagSpecification")
        if tags:
            tags = tags[0].get("Tag")

        if not availability_zone and not availability_zone_id:
            availability_zone = random.choice(
                self.ec2_backend.describe_availability_zones()
            ).name
        subnet = self.ec2_backend.create_subnet(
            vpc_id,
            cidr_block,
            ipv6_cidr_block,
            availability_zone,
            availability_zone_id,
            context=self,
            tags=tags,
        )
        template = self.response_template(CREATE_SUBNET_RESPONSE)
        return template.render(subnet=subnet)

    def delete_subnet(self):
        subnet_id = self._get_param("SubnetId")
        subnet = self.ec2_backend.delete_subnet(subnet_id)
        template = self.response_template(DELETE_SUBNET_RESPONSE)
        return template.render(subnet=subnet)

    def describe_subnets(self):
        subnet_ids = self._get_multi_param("SubnetId")
        filters = filters_from_querystring(self.querystring)
        subnets = self.ec2_backend.get_all_subnets(subnet_ids, filters)
        template = self.response_template(DESCRIBE_SUBNETS_RESPONSE)
        return template.render(subnets=subnets)

    def modify_subnet_attribute(self):
        subnet_id = self._get_param("SubnetId")

        for attribute in ("MapPublicIpOnLaunch", "AssignIpv6AddressOnCreation"):
            if self.querystring.get("%s.Value" % attribute):
                attr_name = camelcase_to_underscores(attribute)
                attr_value = self.querystring.get("%s.Value" % attribute)[0]
                self.ec2_backend.modify_subnet_attribute(
                    subnet_id, attr_name, attr_value
                )
                return MODIFY_SUBNET_ATTRIBUTE_RESPONSE

    def associate_subnet_cidr_block(self):
        ipv6_cidr_block = self._get_param("Ipv6CidrBlock")
        subnet_id = self._get_param("SubnetId")

        association = self.ec2_backend.associate_subnet_cidr_block(
            subnet_id, ipv6_cidr_block
        )
        template = self.response_template(ASSOCIATE_SUBNET_CIDR_BLOCK_RESPONSE)
        return template.render(subnet_id=subnet_id, association=association)

    def disassociate_subnet_cidr_block(self):
        association_id = self._get_param("AssociationId")

        subnet_id, association = self.ec2_backend.disassociate_subnet_cidr_block(
            association_id
        )
        template = self.response_template(DISASSOCIATE_SUBNET_CIDR_BLOCK_RESPONSE)
        result = template.render(subnet_id=subnet_id, association=association)
        return result


CREATE_SUBNET_RESPONSE = """
<CreateSubnetResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
  <subnet>
    <subnetId>{{ subnet.id }}</subnetId>
    <state>pending</state>
    <vpcId>{{ subnet.vpc_id }}</vpcId>
    <cidrBlock>{{ subnet.cidr_block }}</cidrBlock>
    <availableIpAddressCount>{{ subnet.available_ip_addresses or '0' }}</availableIpAddressCount>
    <availabilityZone>{{ subnet._availability_zone.name }}</availabilityZone>
    <availabilityZoneId>{{ subnet._availability_zone.zone_id }}</availabilityZoneId>
    <defaultForAz>{{ subnet.default_for_az }}</defaultForAz>
    <mapPublicIpOnLaunch>{{ subnet.map_public_ip_on_launch }}</mapPublicIpOnLaunch>
    <ownerId>{{ subnet.owner_id }}</ownerId>
    <assignIpv6AddressOnCreation>{{ 'false' if not subnet.assign_ipv6_address_on_creation or subnet.assign_ipv6_address_on_creation == 'false' else 'true'}}</assignIpv6AddressOnCreation>
    <ipv6CidrBlockAssociationSet>
    {% for ipv6_association in subnet.ipv6_cidr_block_associations.values() %}
    {% if ipv6_association.ipv6CidrBlockState == "associated" %}
      <item>
        <ipv6CidrBlock>{{ ipv6_association.ipv6CidrBlock }}</ipv6CidrBlock>
        <associationId>{{ ipv6_association.associationId }}</associationId>
        <ipv6CidrBlockState>
          <state>{{ ipv6_association.ipv6CidrBlockState }}</state>
        </ipv6CidrBlockState>
      </item>
    {% endif %}
    {% endfor %}
    </ipv6CidrBlockAssociationSet>
    <subnetArn>arn:aws:ec2:{{ subnet._availability_zone.name[0:-1] }}:{{ subnet.owner_id }}:subnet/{{ subnet.id }}</subnetArn>
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
        <state>{{ subnet.state }}</state>
        <vpcId>{{ subnet.vpc_id }}</vpcId>
        <cidrBlock>{{ subnet.cidr_block }}</cidrBlock>
        <availableIpAddressCount>{{ subnet.available_ip_addresses or '0' }}</availableIpAddressCount>
        <availabilityZone>{{ subnet._availability_zone.name }}</availabilityZone>
        <availabilityZoneId>{{ subnet._availability_zone.zone_id }}</availabilityZoneId>
        <defaultForAz>{{ subnet.default_for_az }}</defaultForAz>
        <mapPublicIpOnLaunch>{{ subnet.map_public_ip_on_launch }}</mapPublicIpOnLaunch>
        <ownerId>{{ subnet.owner_id }}</ownerId>
        <assignIpv6AddressOnCreation>{{ 'false' if not subnet.assign_ipv6_address_on_creation or subnet.assign_ipv6_address_on_creation == 'false' else 'true'}}</assignIpv6AddressOnCreation>
        <ipv6CidrBlockAssociationSet>
        {% for ipv6_association in subnet.ipv6_cidr_block_associations.values() %}
        {% if ipv6_association.ipv6CidrBlockState == "associated" %}
          <item>
            <ipv6CidrBlock>{{ ipv6_association.ipv6CidrBlock }}</ipv6CidrBlock>
            <associationId>{{ ipv6_association.associationId }}</associationId>
            <ipv6CidrBlockState>
              <state>{{ ipv6_association.ipv6CidrBlockState }}</state>
            </ipv6CidrBlockState>
          </item>
        {% endif %}
        {% endfor %}
        </ipv6CidrBlockAssociationSet>
        <subnetArn>arn:aws:ec2:{{ subnet._availability_zone.name[0:-1] }}:{{ subnet.owner_id }}:subnet/{{ subnet.id }}</subnetArn>
        {% if subnet.get_tags() %}
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
        {% endif %}
      </item>
    {% endfor %}
  </subnetSet>
</DescribeSubnetsResponse>"""

MODIFY_SUBNET_ATTRIBUTE_RESPONSE = """
<ModifySubnetAttributeResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
  <return>true</return>
</ModifySubnetAttributeResponse>"""

ASSOCIATE_SUBNET_CIDR_BLOCK_RESPONSE = """
<AssociateSubnetCidrBlock xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <subnetId>{{ subnet_id }}</subnetId>
  <ipv6CidrBlockAssociation>
    <ipv6CidrBlock>{{ association.ipv6CidrBlock }}</ipv6CidrBlock>
    <ipv6CidrBlockState>
      <state>{{ association.ipv6CidrBlockState }}</state>
    </ipv6CidrBlockState>
    <associationId>{{ association.associationId }}</associationId>
  </ipv6CidrBlockAssociation>
</AssociateSubnetCidrBlock>
"""

DISASSOCIATE_SUBNET_CIDR_BLOCK_RESPONSE = """
<DisassociateSubnetCidrBlockResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <subnetId>{{ subnet_id }}</subnetId>
  <ipv6CidrBlockAssociation>
    <ipv6CidrBlock>{{ association.ipv6CidrBlock }}</ipv6CidrBlock>
    <ipv6CidrBlockState>
      <state>{{ association.ipv6CidrBlockState }}</state>
    </ipv6CidrBlockState>
    <associationId>{{ association.associationId }}</associationId>
  </ipv6CidrBlockAssociation>
</DisassociateSubnetCidrBlockResponse>
"""
