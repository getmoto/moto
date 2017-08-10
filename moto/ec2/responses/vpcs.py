from __future__ import unicode_literals
from moto.core.responses import BaseResponse
from moto.core.utils import camelcase_to_underscores
from moto.ec2.utils import filters_from_querystring, vpc_ids_from_querystring


class VPCs(BaseResponse):

    def create_vpc(self):
        cidr_block = self.querystring.get('CidrBlock')[0]
        instance_tenancy = self.querystring.get(
            'InstanceTenancy', ['default'])[0]
        vpc = self.ec2_backend.create_vpc(cidr_block, instance_tenancy)
        template = self.response_template(CREATE_VPC_RESPONSE)
        return template.render(vpc=vpc)

    def delete_vpc(self):
        vpc_id = self.querystring.get('VpcId')[0]
        vpc = self.ec2_backend.delete_vpc(vpc_id)
        template = self.response_template(DELETE_VPC_RESPONSE)
        return template.render(vpc=vpc)

    def describe_vpcs(self):
        vpc_ids = vpc_ids_from_querystring(self.querystring)
        filters = filters_from_querystring(self.querystring)
        vpcs = self.ec2_backend.get_all_vpcs(vpc_ids=vpc_ids, filters=filters)
        template = self.response_template(DESCRIBE_VPCS_RESPONSE)
        return template.render(vpcs=vpcs)

    def describe_vpc_attribute(self):
        vpc_id = self.querystring.get('VpcId')[0]
        attribute = self.querystring.get('Attribute')[0]
        attr_name = camelcase_to_underscores(attribute)
        value = self.ec2_backend.describe_vpc_attribute(vpc_id, attr_name)
        template = self.response_template(DESCRIBE_VPC_ATTRIBUTE_RESPONSE)
        return template.render(vpc_id=vpc_id, attribute=attribute, value=value)

    def modify_vpc_attribute(self):
        vpc_id = self.querystring.get('VpcId')[0]

        for attribute in ('EnableDnsSupport', 'EnableDnsHostnames'):
            if self.querystring.get('%s.Value' % attribute):
                attr_name = camelcase_to_underscores(attribute)
                attr_value = self.querystring.get('%s.Value' % attribute)[0]
                self.ec2_backend.modify_vpc_attribute(
                    vpc_id, attr_name, attr_value)
                return MODIFY_VPC_ATTRIBUTE_RESPONSE


CREATE_VPC_RESPONSE = """
<CreateVpcResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
   <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
   <vpc>
      <vpcId>{{ vpc.id }}</vpcId>
      <state>pending</state>
      <cidrBlock>{{ vpc.cidr_block }}</cidrBlock>
      <dhcpOptionsId>{% if vpc.dhcp_options %}{{ vpc.dhcp_options.id }}{% else %}dopt-1a2b3c4d2{% endif %}</dhcpOptionsId>
      <instanceTenancy>{{ vpc.instance_tenancy }}</instanceTenancy>
      <tagSet>
        {% for tag in vpc.get_tags() %}
          <item>
            <resourceId>{{ tag.resource_id }}</resourceId>
            <resourceType>{{ tag.resource_type }}</resourceType>
            <key>{{ tag.key }}</key>
            <value>{{ tag.value }}</value>
          </item>
        {% endfor %}
      </tagSet>
   </vpc>
</CreateVpcResponse>"""

DESCRIBE_VPCS_RESPONSE = """
<DescribeVpcsResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
  <vpcSet>
    {% for vpc in vpcs %}
      <item>
        <vpcId>{{ vpc.id }}</vpcId>
        <state>{{ vpc.state }}</state>
        <cidrBlock>{{ vpc.cidr_block }}</cidrBlock>
        <dhcpOptionsId>{% if vpc.dhcp_options %}{{ vpc.dhcp_options.id }}{% else %}dopt-7a8b9c2d{% endif %}</dhcpOptionsId>
        <instanceTenancy>{{ vpc.instance_tenancy }}</instanceTenancy>
        <isDefault>{{ vpc.is_default }}</isDefault>
        <tagSet>
          {% for tag in vpc.get_tags() %}
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
  </vpcSet>
</DescribeVpcsResponse>"""

DELETE_VPC_RESPONSE = """
<DeleteVpcResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
   <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
   <return>true</return>
</DeleteVpcResponse>
"""

DESCRIBE_VPC_ATTRIBUTE_RESPONSE = """
<DescribeVpcAttributeResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
  <vpcId>{{ vpc_id }}</vpcId>
  <{{ attribute }}>
    <value>{{ value }}</value>
  </{{ attribute }}>
</DescribeVpcAttributeResponse>"""

MODIFY_VPC_ATTRIBUTE_RESPONSE = """
<ModifyVpcAttributeResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
  <return>true</return>
</ModifyVpcAttributeResponse>"""
