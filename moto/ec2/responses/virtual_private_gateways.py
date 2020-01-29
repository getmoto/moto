from __future__ import unicode_literals
from moto.core.responses import BaseResponse
from moto.ec2.utils import filters_from_querystring


class VirtualPrivateGateways(BaseResponse):
    def attach_vpn_gateway(self):
        vpn_gateway_id = self._get_param("VpnGatewayId")
        vpc_id = self._get_param("VpcId")
        attachment = self.ec2_backend.attach_vpn_gateway(vpn_gateway_id, vpc_id)
        template = self.response_template(ATTACH_VPN_GATEWAY_RESPONSE)
        return template.render(attachment=attachment)

    def create_vpn_gateway(self):
        type = self._get_param("Type")
        vpn_gateway = self.ec2_backend.create_vpn_gateway(type)
        template = self.response_template(CREATE_VPN_GATEWAY_RESPONSE)
        return template.render(vpn_gateway=vpn_gateway)

    def delete_vpn_gateway(self):
        vpn_gateway_id = self._get_param("VpnGatewayId")
        vpn_gateway = self.ec2_backend.delete_vpn_gateway(vpn_gateway_id)
        template = self.response_template(DELETE_VPN_GATEWAY_RESPONSE)
        return template.render(vpn_gateway=vpn_gateway)

    def describe_vpn_gateways(self):
        filters = filters_from_querystring(self.querystring)
        vpn_gateways = self.ec2_backend.get_all_vpn_gateways(filters)
        template = self.response_template(DESCRIBE_VPN_GATEWAYS_RESPONSE)
        return template.render(vpn_gateways=vpn_gateways)

    def detach_vpn_gateway(self):
        vpn_gateway_id = self._get_param("VpnGatewayId")
        vpc_id = self._get_param("VpcId")
        attachment = self.ec2_backend.detach_vpn_gateway(vpn_gateway_id, vpc_id)
        template = self.response_template(DETACH_VPN_GATEWAY_RESPONSE)
        return template.render(attachment=attachment)


CREATE_VPN_GATEWAY_RESPONSE = """
<CreateVpnGatewayResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
  <vpnGateway>
    <vpnGatewayId>{{ vpn_gateway.id }}</vpnGatewayId>
    <state>available</state>
    <type>{{ vpn_gateway.type }}</type>
    <availabilityZone>us-east-1a</availabilityZone>
    <attachments/>
    <tagSet>
      {% for tag in vpn_gateway.get_tags() %}
        <item>
          <resourceId>{{ tag.resource_id }}</resourceId>
          <resourceType>{{ tag.resource_type }}</resourceType>
          <key>{{ tag.key }}</key>
          <value>{{ tag.value }}</value>
        </item>
      {% endfor %}
    </tagSet>
  </vpnGateway>
</CreateVpnGatewayResponse>"""

DESCRIBE_VPN_GATEWAYS_RESPONSE = """
<DescribeVpnGatewaysResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
  <vpnGatewaySet>
    {% for vpn_gateway in vpn_gateways %}
      <item>
        <vpnGatewayId>{{ vpn_gateway.id }}</vpnGatewayId>
        <state>available</state>
        <type>{{ vpn_gateway.id }}</type>
        <availabilityZone>us-east-1a</availabilityZone>
        <attachments>
          {% for attachment in vpn_gateway.attachments.values() %}
            <item>
              <vpcId>{{ attachment.vpc_id }}</vpcId>
              <state>{{ attachment.state }}</state>
            </item>
          {% endfor %}
        </attachments>
        <tagSet/>
        <tagSet>
          {% for tag in vpn_gateway.get_tags() %}
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
  </vpnGatewaySet>
</DescribeVpnGatewaysResponse>"""

ATTACH_VPN_GATEWAY_RESPONSE = """
<AttachVpnGatewayResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
   <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
   <attachment>
      <vpcId>{{ attachment.vpc_id }}</vpcId>
      <state>{{ attachment.state }}</state>
   </attachment>
</AttachVpnGatewayResponse>"""

DELETE_VPN_GATEWAY_RESPONSE = """
<DeleteVpnGatewayResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
   <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
   <return>true</return>
</DeleteVpnGatewayResponse>
"""

DETACH_VPN_GATEWAY_RESPONSE = """
<DetachVpnGatewayResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
   <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
   <return>true</return>
</DetachVpnGatewayResponse>
"""
