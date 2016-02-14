from __future__ import unicode_literals
from moto.core.responses import BaseResponse
from moto.ec2.utils import filters_from_querystring, vpc_ids_from_querystring


class VPCs(BaseResponse):
    def create_vpc(self):
        cidr_block = self.querystring.get('CidrBlock')[0]
        vpc = self.ec2_backend.create_vpc(cidr_block)
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


CREATE_VPC_RESPONSE = """
<CreateVpcResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
   <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
   <vpc>
      <vpcId>{{ vpc.id }}</vpcId>
      <state>pending</state>
      <cidrBlock>{{ vpc.cidr_block }}</cidrBlock>
      <dhcpOptionsId>dopt-1a2b3c4d2</dhcpOptionsId>
      <instanceTenancy>default</instanceTenancy>
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
        <dhcpOptionsId>dopt-7a8b9c2d</dhcpOptionsId>
        <instanceTenancy>default</instanceTenancy>
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
