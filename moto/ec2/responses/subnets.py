from jinja2 import Template

from moto.ec2.models import ec2_backend


class Subnets(object):
    def create_subnet(self):
        vpc_id = self.querystring.get('VpcId')[0]
        cidr_block = self.querystring.get('CidrBlock')[0]
        subnet = ec2_backend.create_subnet(vpc_id, cidr_block)
        template = Template(CREATE_SUBNET_RESPONSE)
        return template.render(subnet=subnet)

    def delete_subnet(self):
        subnet_id = self.querystring.get('SubnetId')[0]
        subnet = ec2_backend.delete_subnet(subnet_id)
        if subnet:
            template = Template(DELETE_SUBNET_RESPONSE)
            return template.render(subnet=subnet)
        else:
            return "", dict(status=404)

    def describe_subnets(self):
        subnets = ec2_backend.get_all_subnets()
        template = Template(DESCRIBE_SUBNETS_RESPONSE)
        return template.render(subnets=subnets)


CREATE_SUBNET_RESPONSE = """
<CreateSubnetResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
  <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
  <subnet>
    <subnetId>{{ subnet.id }}</subnetId>
    <state>pending</state>
    <vpcId>{{ subnet.vpc.id }}</vpcId>
    <cidrBlock>{{ subnet.cidr_block }}</cidrBlock>
    <availableIpAddressCount>251</availableIpAddressCount>
    <availabilityZone>us-east-1a</availabilityZone>
    <tagSet/>
  </subnet>
</CreateSubnetResponse>"""

DELETE_SUBNET_RESPONSE = """
<DeleteSubnetResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
   <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
   <return>true</return>
</DeleteSubnetResponse>"""

DESCRIBE_SUBNETS_RESPONSE = """
<DescribeSubnetsResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
  <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
  <subnetSet>
    {% for subnet in subnets %}
      <item>
        <subnetId>{{ subnet.id }}</subnetId>
        <state>available</state>
        <vpcId>{{ subnet.vpc.id }}</vpcId>
        <cidrBlock>{{ subnet.cidr_block }}</cidrBlock>
        <availableIpAddressCount>251</availableIpAddressCount>
        <availabilityZone>us-east-1a</availabilityZone>
        <tagSet/>
      </item>
    {% endfor %}
  </subnetSet>
</DescribeSubnetsResponse>"""
