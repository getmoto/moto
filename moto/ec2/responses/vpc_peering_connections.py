from jinja2 import Template

from moto.core.responses import BaseResponse
from moto.ec2.models import ec2_backend


class VPCPeeringConnections(BaseResponse):
    def create_vpc_peering_connection(self):
        vpc = ec2_backend.get_vpc(self.querystring.get('VpcId')[0])
        peer_vpc = ec2_backend.get_vpc(self.querystring.get('PeerVpcId')[0])
        vpc_pcx = ec2_backend.create_vpc_peering_connection(vpc, peer_vpc)
        template = Template(CREATE_VPC_PEERING_CONNECTION_RESPONSE)
        return template.render(vpc_pcx=vpc_pcx)

    def delete_vpc_peering_connection(self):
        vpc_pcx_id = self.querystring.get('VpcPeeringConnectionId')[0]
        vpc_pcx = ec2_backend.delete_vpc_peering_connection(vpc_pcx_id)
        if vpc_pcx:
            template = Template(DELETE_VPC_PEERING_CONNECTION_RESPONSE)
            return template.render(vpc_pcx=vpc_pcx)
        else:
            return "", dict(status=404)

    def describe_vpc_peering_connections(self):
        vpc_pcxs = ec2_backend.get_all_vpc_peering_connections()
        template = Template(DESCRIBE_VPC_PEERING_CONNECTIONS_RESPONSE)
        return template.render(vpc_pcxs=vpc_pcxs)

    def accept_vpc_peering_connection(self):
        vpc_pcx_id = self.querystring.get('VpcPeeringConnectionId')[0]
        vpc_pcx = ec2_backend.accept_vpc_peering_connection(vpc_pcx_id)
        if vpc_pcx:
            template = Template(ACCEPT_VPC_PEERING_CONNECTION_RESPONSE)
            return template.render(vpc_pcx=vpc_pcx)
        else:
            return "", dict(status=404)

    def reject_vpc_peering_connection(self):
        vpc_pcx_id = self.querystring.get('VpcPeeringConnectionId')[0]
        vpc_pcx = ec2_backend.reject_vpc_peering_connection(vpc_pcx_id)
        if vpc_pcx:
            template = Template(REJECT_VPC_PEERING_CONNECTION_RESPONSE)
            return template.render()
        else:
            return "", dict(status=404)


CREATE_VPC_PEERING_CONNECTION_RESPONSE = """
<CreateVpcPeeringConnectionResponse xmlns="http://ec2.amazonaws.com/doc/2014-06-15/">
  <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
  <vpcPeeringConnection>
    <vpcPeeringConnectionId>{{ vpc_pcx.id }}</vpcPeeringConnectionId>
    <requesterVpcInfo>
      <ownerId>777788889999</ownerId>
      <vpcId>{{ vpc_pcx.vpc.id }}</vpcId>
      <cidrBlock>{{ vpc_pcx.vpc.cidr_block }}</cidrBlock>
    </requesterVpcInfo>
    <accepterVpcInfo>
      <ownerId>123456789012</ownerId>
      <vpcId>{{ vpc_pcx.peer_vpc.id }}</vpcId>
    </accepterVpcInfo>
    <status>
      <code>initiating-request</code>
      <message>Initiating request to {accepter ID}.</message>
    </status>
    <expirationTime>2014-02-18T14:37:25.000Z</expirationTime>
    <tagSet/>
  </vpcPeeringConnection>
</CreateVpcPeeringConnectionResponse>
"""

DESCRIBE_VPC_PEERING_CONNECTIONS_RESPONSE = """
<DescribeVpcPeeringConnectionsResponse xmlns="http://ec2.amazonaws.com/doc/2014-06-15/">
  <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
  <vpcPeeringConnectionSet>
    {% for vpc_pcx in vpc_pcxs %}
      <item>
        <vpcPeeringConnectionId>{{ vpc_pcx.id }}</vpcPeeringConnectionId>
        <requesterVpcInfo>
          <ownerId>777788889999</ownerId>
          <vpcId>{{ vpc_pcx.vpc.id }}</vpcId>
          <cidrBlock>{{ vpc_pcx.vpc.cidr_block }}</cidrBlock>
        </requesterVpcInfo>
        <accepterVpcInfo>
          <ownerId>111122223333</ownerId>
          <vpcId>{{ vpc_pcx.peer_vpc.id }}</vpcId>
        </accepterVpcInfo>
        <status>
          <code>{{ vpc_pcx._status.code }}</code>
          <message>{{ vpc_pcx._status.message }}</message>
        </status>
        <expirationTime>2014-02-17T16:00:50.000Z</expirationTime>
        <tagSet/>
      </item>
    {% endfor %}
  </vpcPeeringConnectionSet>
</DescribeVpcPeeringConnectionsResponse>
"""

DELETE_VPC_PEERING_CONNECTION_RESPONSE = """
<DeleteVpcPeeringConnectionResponse xmlns="http://ec2.amazonaws.com/doc/2014-06-15/">
  <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
  <return>true</return>
</DeleteVpcPeeringConnectionResponse>
"""

ACCEPT_VPC_PEERING_CONNECTION_RESPONSE = """
<AcceptVpcPeeringConnectionResponse xmlns="http://ec2.amazonaws.com/doc/2014-06-15/">
  <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
  <vpcPeeringConnection>
    <vpcPeeringConnectionId>{{ vpc_pcx.id }}</vpcPeeringConnectionId>
    <requesterVpcInfo>
      <ownerId>123456789012</ownerId>
      <vpcId>{{ vpc_pcx.vpc.id }}</vpcId>
      <cidrBlock>{{ vpc_pcx.vpc.cidr_block }}</cidrBlock>
    </requesterVpcInfo>
    <accepterVpcInfo>
      <ownerId>777788889999</ownerId>
      <vpcId>{{ vpc_pcx.peer_vpc.id }}</vpcId>
      <cidrBlock>{{ vpc_pcx.peer_vpc.cidr_block }}</cidrBlock>
    </accepterVpcInfo>
    <status>
      <code>{{ vpc_pcx._status.code }}</code>
      <message>{{ vpc_pcx._status.message }}</message>
    </status>
    <tagSet/>
  </vpcPeeringConnection>
</AcceptVpcPeeringConnectionResponse>
"""

REJECT_VPC_PEERING_CONNECTION_RESPONSE = """
<RejectVpcPeeringConnectionResponse xmlns="http://ec2.amazonaws.com/doc/2014-06-15/">
  <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
  <return>true</return>
</RejectVpcPeeringConnectionResponse>
"""

