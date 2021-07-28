from __future__ import unicode_literals
from moto.core.responses import BaseResponse
from moto.ec2.utils import filters_from_querystring


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
            options=options,
        )
        template = self.response_template(CREATE_TRANSIT_GATEWAY_VPC_ATTACHMENT)
        return template.render(transit_gateway_attachment=transit_gateway_attachment)

    def describe_transit_gateway_vpc_attachments(self):
        transit_gateways_attachment_ids = self._get_multi_param(
            "TransitGatewayAttachmentIds"
        )
        filters = filters_from_querystring(self.querystring)
        max_results = self._get_param("MaxResults")
        transit_gateway_vpc_attachments = self.ec2_backend.describe_transit_gateway_vpc_attachments(
            transit_gateways_attachment_ids=transit_gateways_attachment_ids,
            filters=filters,
            max_results=max_results,
        )
        template = self.response_template(DESCRIBE_TRANSIT_GATEWAY_VPC_ATTACHMENTS)
        return template.render(
            transit_gateway_vpc_attachments=transit_gateway_vpc_attachments
        )

    def describe_transit_gateway_attachments(self):
        transit_gateways_attachment_ids = self._get_multi_param(
            "TransitGatewayAttachmentIds"
        )
        filters = filters_from_querystring(self.querystring)
        max_results = self._get_param("MaxResults")
        transit_gateway_attachments = self.ec2_backend.describe_transit_gateway_attachments(
            transit_gateways_attachment_ids=transit_gateways_attachment_ids,
            filters=filters,
            max_results=max_results,
        )
        template = self.response_template(DESCRIBE_TRANSIT_GATEWAY_ATTACHMENTS)
        return template.render(transit_gateway_attachments=transit_gateway_attachments)


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


DESCRIBE_TRANSIT_GATEWAY_ATTACHMENTS = """<DescribeTransitGatewayAttachmentsResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">
    <requestId>92aa7885-74c0-42d1-a846-e59bd07488a7</requestId>
    <transitGatewayAttachments>
        {% for transit_gateway_attachment in transit_gateway_attachments %}
        <item>
            <association>
                <state>associated</state>
                <transitGatewayRouteTableId>tgw-rtb-0b36edb9b88f0d5e3</transitGatewayRouteTableId>
            </association>
            <creationTime>2021-07-18T08:57:21.000Z</creationTime>
            <resourceId>{{ transit_gateway_attachment.resource_id }}</resourceId>
            <resourceOwnerId>{{ transit_gateway_attachment.resource_owner_id }}</resourceOwnerId>
            <resourceType>{{ transit_gateway_attachment.resource_type }}</resourceType>
            <state>{{ transit_gateway_attachment.state }}</state>
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
            <transitGatewayOwnerId>{{ transit_gateway_attachment.resource_owner_id }}</transitGatewayOwnerId>
        </item>
        {% endfor %}
    </transitGatewayAttachments>
</DescribeTransitGatewayAttachmentsResponse>
"""


DESCRIBE_TRANSIT_GATEWAY_VPC_ATTACHMENTS = """<DescribeTransitGatewayVpcAttachmentsResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">
        <requestId>bebc9670-0205-4f28-ad89-049c97e46633</requestId>
        <transitGatewayVpcAttachments>
        {% for transit_gateway_vpc_attachment in transit_gateway_vpc_attachments %}
            <item>
                <creationTime>2021-07-18T08:57:21.000Z</creationTime>
                <options>
                    <applianceModeSupport>{{ transit_gateway_vpc_attachment.options.ApplianceModeSupport }}</applianceModeSupport>
                    <dnsSupport>{{ transit_gateway_vpc_attachment.options.DnsSupport }}</dnsSupport>
                    <ipv6Support>{{ transit_gateway_vpc_attachment.options.Ipv6Support }}</ipv6Support>
                </options>
                <state>{{ transit_gateway_vpc_attachment.state }}</state>
                <subnetIds>
                {% for id in transit_gateway_vpc_attachment.subnet_ids %}
                    <item>{{ id }}</item>
                {% endfor %}
                </subnetIds>
                <tagSet>
                {% for tag in transit_gateway_vpc_attachment.get_tags() %}
                    <item>
                        <key>{{ tag.key }}</key>
                        <value>{{ tag.value }}</value>
                    </item>
                {% endfor %}
                </tagSet>
                <transitGatewayAttachmentId>{{ transit_gateway_vpc_attachment.id }}</transitGatewayAttachmentId>
                <transitGatewayId>{{ transit_gateway_vpc_attachment.transit_gateway_id }}</transitGatewayId>
                <vpcId>{{ transit_gateway_vpc_attachment.vpc_id }}</vpcId>
                <vpcOwnerId>{{ transit_gateway_vpc_attachment.resource_owner_id }}</vpcOwnerId>
            </item>
        {% endfor %}
    </transitGatewayVpcAttachments>
</DescribeTransitGatewayVpcAttachmentsResponse>
"""
