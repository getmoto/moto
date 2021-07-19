from __future__ import unicode_literals
from moto.core.responses import BaseResponse


class TransitGatewayAttachment(BaseResponse):
    def create_transit_gateway_vpc_attachment(self):
        options = self._get_multi_param_dict("Options")
        subnet_ids = self._get_multi_param("SubnetIds")
        transit_gateway_id = self._get_param("TransitGatewayId")
        vpc_id = self._get_param("VpcId")

        tags = self._get_multi_param("TagSpecifications")
        tags = tags[0] if isinstance(tags, list) and len(tags) == 1 else tags
        tags = (tags or {}).get("Tag", [])
        tags = {t["Key"]: t["Value"] for t in tags}

        transit_gateway_attachment = self.ec2_backend.create_transit_gateway_vpc_attachment(
            transit_gateway_id=transit_gateway_id,
            tags=tags,
            vpc_id=vpc_id,
            subnet_ids=subnet_ids,
            options=options
        )
        template = self.response_template(CREATE_TRANSIT_GATEWAY_VPC_ATTACHMENT)
        return template.render(transit_gateway_attachment=transit_gateway_attachment)


CREATE_TRANSIT_GATEWAY_VPC_ATTACHMENT = """<CreateTransitGatewayVpcAttachmentResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">
        <requestId>9b5766ac-2af6-4b92-9a8a-4d74ae46ae79</requestId>
        <transitGatewayVpcAttachment>
            <createTime>{{ transit_gateway_attachment.create_time }}</createTime>
            <options>
                <applianceModeSupport>{{ transit_gateway_attachment.options.ApplianceModeSupport }}</applianceModeSupport>
                <dnsSupport>{{ transit_gateway_attachment.options.DnsSupport }}</dnsSupport>
                <ipv6Support>{{ transit_gateway_attachment.options.Ipv6Support }}</ipv6Support>
            </options>
            <state>{{ transit_gateway_attachment.state }}</state>
            <subnetIds>
            {% for subnet_id in transit_gateway_attachment.subnet_ids %}
                <item>{{ subnet_id }}</item>
            {% endfor %}
            </subnetIds>
            <tagSet>
            {% for tag in transit_gateway_attachment.get_tags() %}
                <item>
                    <key>{{ tag.key }}</key>
                    <value>{{ tag.value }}</value>
                </item>
            {% endfor %}
            </tagSet>
            <transitGatewayAttachmentId>{{ transit_gateway_attachment.id }}</transitGatewayAttachmentId>
            <transitGatewayId>{{ transit_gateway_attachment.transit_gateway_id }}</transitGatewayId>
            <vpcId>{{ transit_gateway_attachment.vpc_id }}</vpcId>
            <vpcOwnerId>{{ transit_gateway_attachment.resource_owner_id }}</vpcOwnerId>
    </transitGatewayVpcAttachment>
</CreateTransitGatewayVpcAttachmentResponse>"""
