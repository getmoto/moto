from __future__ import unicode_literals
from moto.core.responses import BaseResponse
from moto.ec2.utils import filters_from_querystring


class TransitGateways(BaseResponse):
    def create_transit_gateway(self):
        description = self._get_param("Description") or None
        options = self._get_multi_param_dict("Options")
        tags = self._get_multi_param("TagSpecification")
        tags = tags[0] if isinstance(tags, list) and len(tags) == 1 else tags
        tags = (tags or {}).get("Tag", [])
        tags = {t["Key"]: t["Value"] for t in tags}

        transit_gateway = self.ec2_backend.create_transit_gateway(
            description=description, options=options, tags=tags
        )
        template = self.response_template(CREATE_TRANSIT_GATEWAY_RESPONSE)
        return template.render(transit_gateway=transit_gateway)

    def delete_transit_gateway(self):
        transit_gateway_id = self._get_param("TransitGatewayId")
        transit_gateway = self.ec2_backend.delete_transit_gateway(transit_gateway_id)
        template = self.response_template(DELETE_TRANSIT_GATEWAY_RESPONSE)
        return template.render(transit_gateway=transit_gateway)

    def describe_transit_gateways(self):
        filters = filters_from_querystring(self.querystring)
        transit_gateways = self.ec2_backend.get_all_transit_gateways(filters)
        template = self.response_template(DESCRIBE_TRANSIT_GATEWAY_RESPONSE)
        return template.render(transit_gateways=transit_gateways)

    def modify_transit_gateway(self):
        transit_gateway_id = self._get_param("TransitGatewayId")
        description = self._get_param("Description") or None
        options = self._get_multi_param_dict("Options")
        transit_gateway = self.ec2_backend.modify_transit_gateway(
            transit_gateway_id=transit_gateway_id, description=description, options=options
        )
        template = self.response_template(MODIFY_TRANSIT_GATEWAY_RESPONSE)
        return template.render(transit_gateway=transit_gateway)


CREATE_TRANSIT_GATEWAY_RESPONSE = """<CreateTransitGatewayResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">
    <requestId>151283df-f7dc-4317-89b4-01c9888b1d45</requestId>
    <transitGateway>
        <transitGatewayId>{{ transit_gateway.id }}</transitGatewayId>
        <ownerId>{{ transit_gateway.owner_id }}</ownerId>
        <description>{{ transit_gateway.description }}</description>
        <createTime>{{ transit_gateway.create_time }}</createTime>
        <state>{{ transit_gateway.state }}</state>
        {% if transit_gateway.options %}
            <options>
                <amazonSideAsn>{{ transit_gateway.options.AmazonSideAsn or "64512" }}</amazonSideAsn>
                <associationDefaultRouteTableId>{{ transit_gateway.options.AutoAcceptSharedAttachments or "tgw-rtb-0d571391e50cf8514" }}</associationDefaultRouteTableId>
                <autoAcceptSharedAttachments>{{ transit_gateway.options.AutoAcceptSharedAttachments or "disable" }}</autoAcceptSharedAttachments>
                <defaultRouteTableAssociation>{{ transit_gateway.options.DefaultRouteTableAssociation or "enable" }}</defaultRouteTableAssociation>
                <defaultRouteTablePropagation>{{ transit_gateway.options.DefaultRouteTablePropagation or "enable" }}</defaultRouteTablePropagation>
                <dnsSupport>{{ transit_gateway.options.DnsSupport or "enable" }}</dnsSupport>
                <propagationDefaultRouteTableId>{{ transit_gateway.options.propagationDefaultRouteTableId or "enable" }}</propagationDefaultRouteTableId>
                <vpnEcmpSupport>{{ transit_gateway.options.VpnEcmpSupport or "enable" }}</vpnEcmpSupport>
            </options>
        {% endif %}
        <tagSet>
            {% for tag in transit_gateway.get_tags() %}
                <item>
                    <key>{{ tag.key }}</key>
                    <value>{{ tag.value }}</value>
                </item>
            {% endfor %}
        </tagSet>
    </transitGateway>
</CreateTransitGatewayResponse>
"""

DESCRIBE_TRANSIT_GATEWAY_RESPONSE = """<DescribeTransitGatewaysResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">
    <requestId>151283df-f7dc-4317-89b4-01c9888b1d45</requestId>
    <transitGatewaySet>
    {% for transit_gateway in transit_gateways %}
        <item>
            <creationTime>{{ transit_gateway.create_time }}</creationTime>
            <description>{{ transit_gateway.description if transit_gateway.description != None }}</description>
            {% if transit_gateway.options %}
                <options>
                    <amazonSideAsn>{{ transit_gateway.options.AmazonSideAsn or "64512" }}</amazonSideAsn>
                    <associationDefaultRouteTableId>{{ transit_gateway.options.AutoAcceptSharedAttachments or "tgw-rtb-0d571391e50cf8514" }}</associationDefaultRouteTableId>
                    <autoAcceptSharedAttachments>{{ transit_gateway.options.AutoAcceptSharedAttachments or "disable" }}</autoAcceptSharedAttachments>
                    <defaultRouteTableAssociation>{{ transit_gateway.options.DefaultRouteTableAssociation or "enable" }}</defaultRouteTableAssociation>
                    <defaultRouteTablePropagation>{{ transit_gateway.options.DefaultRouteTablePropagation or "enable" }}</defaultRouteTablePropagation>
                    <dnsSupport>{{ transit_gateway.options.DnsSupport or "enable" }}</dnsSupport>
                    <propagationDefaultRouteTableId>{{ transit_gateway.options.propagationDefaultRouteTableId or "enable" }}</propagationDefaultRouteTableId>
                    <vpnEcmpSupport>{{ transit_gateway.options.VpnEcmpSupport or "enable" }}</vpnEcmpSupport>
                </options>
            {% endif %}
            <ownerId>{{ transit_gateway.owner_id }}</ownerId>
            <state>{{ transit_gateway.state }}</state>
            <tagSet>
                {% for tag in transit_gateway.get_tags() %}
                    <item>
                        <key>{{ tag.key }}</key>
                        <value>{{ tag.value }}</value>
                    </item>
                {% endfor %}
            </tagSet>
            <transitGatewayArn>arn:aws:ec2:us-east-1:{{ transit_gateway.owner_id }}:transit-gateway/{{ transit_gateway.id }}</transitGatewayArn>
            <transitGatewayId>{{ transit_gateway.id }}</transitGatewayId>
        </item>
    {% endfor %}
    </transitGatewaySet>
</DescribeTransitGatewaysResponse>
"""

DELETE_TRANSIT_GATEWAY_RESPONSE = """<DeleteTransitGatewayResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">
    <requestId>151283df-f7dc-4317-89b4-01c9888b1d45</requestId>
    <transitGatewayId>{{ transit_gateway.id }}</transitGatewayId>
</DeleteTransitGatewayResponse>
"""


MODIFY_TRANSIT_GATEWAY_RESPONSE = """<ModifyTransitGatewaysResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">
    <requestId>151283df-f7dc-4317-89b4-01c9888b1d45</requestId>
    <transitGatewaySet>
    <item>
        <creationTime>{{ transit_gateway.create_time }}</creationTime>
        <description>{{ transit_gateway.description if transit_gateway.description != None }}</description>
        {% if transit_gateway.options %}
        <options>
            <amazonSideAsn>{{ transit_gateway.options.AmazonSideAsn or "64512" }}</amazonSideAsn>
            <associationDefaultRouteTableId>{{ transit_gateway.options.AutoAcceptSharedAttachments or "tgw-rtb-0d571391e50cf8514" }}</associationDefaultRouteTableId>
            <autoAcceptSharedAttachments>{{ transit_gateway.options.AutoAcceptSharedAttachments or "disable" }}</autoAcceptSharedAttachments>
            <defaultRouteTableAssociation>{{ transit_gateway.options.DefaultRouteTableAssociation or "enable" }}</defaultRouteTableAssociation>
            <defaultRouteTablePropagation>{{ transit_gateway.options.DefaultRouteTablePropagation or "enable" }}</defaultRouteTablePropagation>
            <dnsSupport>{{ transit_gateway.options.DnsSupport or "enable" }}</dnsSupport>
            <propagationDefaultRouteTableId>{{ transit_gateway.options.propagationDefaultRouteTableId or "enable" }}</propagationDefaultRouteTableId>
            <vpnEcmpSupport>{{ transit_gateway.options.VpnEcmpSupport or "enable" }}</vpnEcmpSupport>
        </options>
        {% endif %}
        <ownerId>{{ transit_gateway.owner_id }}</ownerId>
        <state>{{ transit_gateway.state }}</state>
        <tagSet>
            {% for tag in transit_gateway.get_tags() %}
                <item>
                    <key>{{ tag.key }}</key>
                    <value>{{ tag.value }}</value>
                </item>
            {% endfor %}
        </tagSet>
        <transitGatewayArn>arn:aws:ec2:us-east-1:{{ transit_gateway.owner_id }}:transit-gateway/{{ transit_gateway.id }}</transitGatewayArn>
        <transitGatewayId>{{ transit_gateway.id }}</transitGatewayId>
    </item>
    </transitGatewaySet>
</ModifyTransitGatewaysResponse>
"""
