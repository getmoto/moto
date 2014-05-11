from jinja2 import Template

from moto.core.responses import BaseResponse
from moto.ec2.models import ec2_backend


class VPCs(BaseResponse):
    def create_vpc(self):
        cidr_block = self.querystring.get('CidrBlock')[0]
        vpc = ec2_backend.create_vpc(cidr_block)
        template = Template(CREATE_VPC_RESPONSE)
        return template.render(vpc=vpc)

    def delete_vpc(self):
        vpc_id = self.querystring.get('VpcId')[0]
        vpc = ec2_backend.delete_vpc(vpc_id)
        if vpc:
            template = Template(DELETE_VPC_RESPONSE)
            return template.render(vpc=vpc)
        else:
            return "", dict(status=404)

    def describe_vpcs(self):
        vpcs = ec2_backend.get_all_vpcs()
        template = Template(DESCRIBE_VPCS_RESPONSE)
        return template.render(vpcs=vpcs)


CREATE_VPC_RESPONSE = """
<CreateVpcResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
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
<DescribeVpcsResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
  <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
  <vpcSet>
    {% for vpc in vpcs %}
      <item>
        <vpcId>{{ vpc.id }}</vpcId>
        <state>available</state>
        <cidrBlock>{{ vpc.cidr_block }}</cidrBlock>
        <dhcpOptionsId>dopt-7a8b9c2d</dhcpOptionsId>
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
      </item>
    {% endfor %}
  </vpcSet>
</DescribeVpcsResponse>"""

DELETE_VPC_RESPONSE = """
<DeleteVpcResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
   <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
   <return>true</return>
</DeleteVpcResponse>
"""
