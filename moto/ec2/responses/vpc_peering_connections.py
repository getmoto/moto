from __future__ import unicode_literals
from moto.core.responses import BaseResponse


class VPCPeeringConnections(BaseResponse):

    def create_vpc_peering_connection(self):
        vpc = self.ec2_backend.get_vpc(self._get_param('VpcId'))
        peer_vpc = self.ec2_backend.get_vpc(self._get_param('PeerVpcId'))
        vpc_pcx = self.ec2_backend.create_vpc_peering_connection(vpc, peer_vpc)
        template = self.response_template(
            CREATE_VPC_PEERING_CONNECTION_RESPONSE)
        return template.render(vpc_pcx=vpc_pcx)

    def delete_vpc_peering_connection(self):
        vpc_pcx_id = self._get_param('VpcPeeringConnectionId')
        vpc_pcx = self.ec2_backend.delete_vpc_peering_connection(vpc_pcx_id)
        template = self.response_template(
            DELETE_VPC_PEERING_CONNECTION_RESPONSE)
        return template.render(vpc_pcx=vpc_pcx)

    def describe_vpc_peering_connections(self):
        vpc_pcxs = self.ec2_backend.get_all_vpc_peering_connections()
        template = self.response_template(
            DESCRIBE_VPC_PEERING_CONNECTIONS_RESPONSE)
        return template.render(vpc_pcxs=vpc_pcxs)

    def accept_vpc_peering_connection(self):
        vpc_pcx_id = self._get_param('VpcPeeringConnectionId')
        vpc_pcx = self.ec2_backend.accept_vpc_peering_connection(vpc_pcx_id)
        template = self.response_template(
            ACCEPT_VPC_PEERING_CONNECTION_RESPONSE)
        return template.render(vpc_pcx=vpc_pcx)

    def reject_vpc_peering_connection(self):
        vpc_pcx_id = self._get_param('VpcPeeringConnectionId')
        self.ec2_backend.reject_vpc_peering_connection(vpc_pcx_id)
        template = self.response_template(
            REJECT_VPC_PEERING_CONNECTION_RESPONSE)
        return template.render()


CREATE_VPC_PEERING_CONNECTION_RESPONSE = """
<CreateVpcPeeringConnectionResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
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
<DescribeVpcPeeringConnectionsResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
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
          <ownerId>123456789012</ownerId>
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
<DeleteVpcPeeringConnectionResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
  <return>true</return>
</DeleteVpcPeeringConnectionResponse>
"""

ACCEPT_VPC_PEERING_CONNECTION_RESPONSE = """
<AcceptVpcPeeringConnectionResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
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
<RejectVpcPeeringConnectionResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
  <return>true</return>
</RejectVpcPeeringConnectionResponse>
"""
