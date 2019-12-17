from __future__ import unicode_literals
from moto.core.responses import BaseResponse
from moto.core import ACCOUNT_ID


class VPCPeeringConnections(BaseResponse):
    def create_vpc_peering_connection(self):
        peer_region = self._get_param("PeerRegion")
        if peer_region == self.region or peer_region is None:
            peer_vpc = self.ec2_backend.get_vpc(self._get_param("PeerVpcId"))
        else:
            peer_vpc = self.ec2_backend.get_cross_vpc(
                self._get_param("PeerVpcId"), peer_region
            )
        vpc = self.ec2_backend.get_vpc(self._get_param("VpcId"))
        vpc_pcx = self.ec2_backend.create_vpc_peering_connection(vpc, peer_vpc)
        template = self.response_template(CREATE_VPC_PEERING_CONNECTION_RESPONSE)
        return template.render(vpc_pcx=vpc_pcx)

    def delete_vpc_peering_connection(self):
        vpc_pcx_id = self._get_param("VpcPeeringConnectionId")
        vpc_pcx = self.ec2_backend.delete_vpc_peering_connection(vpc_pcx_id)
        template = self.response_template(DELETE_VPC_PEERING_CONNECTION_RESPONSE)
        return template.render(vpc_pcx=vpc_pcx)

    def describe_vpc_peering_connections(self):
        vpc_pcxs = self.ec2_backend.get_all_vpc_peering_connections()
        template = self.response_template(DESCRIBE_VPC_PEERING_CONNECTIONS_RESPONSE)
        return template.render(vpc_pcxs=vpc_pcxs)

    def accept_vpc_peering_connection(self):
        vpc_pcx_id = self._get_param("VpcPeeringConnectionId")
        vpc_pcx = self.ec2_backend.accept_vpc_peering_connection(vpc_pcx_id)
        template = self.response_template(ACCEPT_VPC_PEERING_CONNECTION_RESPONSE)
        return template.render(vpc_pcx=vpc_pcx)

    def reject_vpc_peering_connection(self):
        vpc_pcx_id = self._get_param("VpcPeeringConnectionId")
        self.ec2_backend.reject_vpc_peering_connection(vpc_pcx_id)
        template = self.response_template(REJECT_VPC_PEERING_CONNECTION_RESPONSE)
        return template.render()


CREATE_VPC_PEERING_CONNECTION_RESPONSE = (
    """
<CreateVpcPeeringConnectionResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">
 <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
 <vpcPeeringConnection>
  <vpcPeeringConnectionId>{{ vpc_pcx.id }}</vpcPeeringConnectionId>
    <requesterVpcInfo>
     <ownerId>777788889999</ownerId>
     <vpcId>{{ vpc_pcx.vpc.id }}</vpcId>
     <cidrBlock>{{ vpc_pcx.vpc.cidr_block }}</cidrBlock>
     <peeringOptions>
       <allowEgressFromLocalClassicLinkToRemoteVpc>false</allowEgressFromLocalClassicLinkToRemoteVpc>
       <allowEgressFromLocalVpcToRemoteClassicLink>false</allowEgressFromLocalVpcToRemoteClassicLink>
       <allowDnsResolutionFromRemoteVpc>false</allowDnsResolutionFromRemoteVpc>
     </peeringOptions>
    </requesterVpcInfo>
    <accepterVpcInfo>
      <ownerId>"""
    + ACCOUNT_ID
    + """</ownerId>
      <vpcId>{{ vpc_pcx.peer_vpc.id }}</vpcId>
    </accepterVpcInfo>
    <status>
     <code>initiating-request</code>
     <message>Initiating Request to {accepter ID}</message>
    </status>
    <expirationTime>2014-02-18T14:37:25.000Z</expirationTime>
    <tagSet/>
 </vpcPeeringConnection>
</CreateVpcPeeringConnectionResponse>
"""
)

DESCRIBE_VPC_PEERING_CONNECTIONS_RESPONSE = (
    """
<DescribeVpcPeeringConnectionsResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">
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
     <ownerId>"""
    + ACCOUNT_ID
    + """</ownerId>
     <vpcId>{{ vpc_pcx.peer_vpc.id }}</vpcId>
     <cidrBlock>{{ vpc_pcx.peer_vpc.cidr_block }}</cidrBlock>
     <peeringOptions>
        <allowEgressFromLocalClassicLinkToRemoteVpc>false</allowEgressFromLocalClassicLinkToRemoteVpc>
        <allowEgressFromLocalVpcToRemoteClassicLink>true</allowEgressFromLocalVpcToRemoteClassicLink>
        <allowDnsResolutionFromRemoteVpc>false</allowDnsResolutionFromRemoteVpc>
     </peeringOptions>
    </accepterVpcInfo>
     <status>
      <code>{{ vpc_pcx._status.code }}</code>
      <message>{{ vpc_pcx._status.message }}</message>
     </status>
     <tagSet/>
 </item>
 {% endfor %}
 </vpcPeeringConnectionSet>
</DescribeVpcPeeringConnectionsResponse>
"""
)

DELETE_VPC_PEERING_CONNECTION_RESPONSE = """
<DeleteVpcPeeringConnectionResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
  <return>true</return>
</DeleteVpcPeeringConnectionResponse>
"""

ACCEPT_VPC_PEERING_CONNECTION_RESPONSE = (
    """
<AcceptVpcPeeringConnectionResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">
  <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
  <vpcPeeringConnection>
    <vpcPeeringConnectionId>{{ vpc_pcx.id }}</vpcPeeringConnectionId>
    <requesterVpcInfo>
      <ownerId>777788889999</ownerId>
      <vpcId>{{ vpc_pcx.vpc.id }}</vpcId>
      <cidrBlock>{{ vpc_pcx.vpc.cidr_block }}</cidrBlock>
    </requesterVpcInfo>
    <accepterVpcInfo>
      <ownerId>"""
    + ACCOUNT_ID
    + """</ownerId>
      <vpcId>{{ vpc_pcx.peer_vpc.id }}</vpcId>
      <cidrBlock>{{ vpc_pcx.peer_vpc.cidr_block }}</cidrBlock>
      <peeringOptions>
        <allowEgressFromLocalClassicLinkToRemoteVpc>false</allowEgressFromLocalClassicLinkToRemoteVpc>
        <allowEgressFromLocalVpcToRemoteClassicLink>false</allowEgressFromLocalVpcToRemoteClassicLink>
        <allowDnsResolutionFromRemoteVpc>false</allowDnsResolutionFromRemoteVpc>
      </peeringOptions>
    </accepterVpcInfo>
    <status>
      <code>{{ vpc_pcx._status.code }}</code>
      <message>{{ vpc_pcx._status.message }}</message>
    </status>
    <tagSet/>
  </vpcPeeringConnection>
</AcceptVpcPeeringConnectionResponse>
"""
)

REJECT_VPC_PEERING_CONNECTION_RESPONSE = """
<RejectVpcPeeringConnectionResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
  <return>true</return>
</RejectVpcPeeringConnectionResponse>
"""
