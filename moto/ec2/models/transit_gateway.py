from datetime import datetime
from moto.core import CloudFormationModel
from moto.core.utils import iso_8601_datetime_with_milliseconds
from moto.utilities.utils import filter_resources, merge_multiple_dicts
from .core import TaggedEC2Resource
from ..utils import random_transit_gateway_id


class TransitGateway(TaggedEC2Resource, CloudFormationModel):
    DEFAULT_OPTIONS = {
        "AmazonSideAsn": "64512",
        "AssociationDefaultRouteTableId": "tgw-rtb-0d571391e50cf8514",
        "AutoAcceptSharedAttachments": "disable",
        "DefaultRouteTableAssociation": "enable",
        "DefaultRouteTablePropagation": "enable",
        "DnsSupport": "enable",
        "MulticastSupport": "disable",
        "PropagationDefaultRouteTableId": "tgw-rtb-0d571391e50cf8514",
        "TransitGatewayCidrBlocks": None,
        "VpnEcmpSupport": "enable",
    }

    def __init__(self, backend, description=None, options=None):
        self.ec2_backend = backend
        self.id = random_transit_gateway_id()
        self.description = description
        self.state = "available"
        self.options = merge_multiple_dicts(self.DEFAULT_OPTIONS, options or {})
        self._created_at = datetime.utcnow()

    @property
    def physical_resource_id(self):
        return self.id

    @property
    def create_time(self):
        return iso_8601_datetime_with_milliseconds(self._created_at)

    @property
    def owner_id(self):
        return self.ec2_backend.account_id

    @staticmethod
    def cloudformation_name_type():
        return None

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ec2-natgateway.html
        return "AWS::EC2::TransitGateway"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, account_id, region_name, **kwargs
    ):
        from ..models import ec2_backends

        ec2_backend = ec2_backends[account_id][region_name]
        properties = cloudformation_json["Properties"]
        description = properties["Description"]
        options = dict(properties)
        del options["Description"]
        transit_gateway = ec2_backend.create_transit_gateway(
            description=description, options=options
        )

        for tag in properties.get("Tags", []):
            tag_key = tag["Key"]
            tag_value = tag["Value"]
            transit_gateway.add_tag(tag_key, tag_value)

        return transit_gateway


class TransitGatewayBackend:
    def __init__(self):
        self.transit_gateways = {}

    def create_transit_gateway(self, description=None, options=None, tags=None):
        transit_gateway = TransitGateway(self, description, options)
        for tag in tags or []:
            tag_key = tag.get("Key")
            tag_value = tag.get("Value")
            transit_gateway.add_tag(tag_key, tag_value)

        self.transit_gateways[transit_gateway.id] = transit_gateway
        return transit_gateway

    def describe_transit_gateways(self, filters, transit_gateway_ids):
        transit_gateways = list(self.transit_gateways.copy().values())

        if transit_gateway_ids:
            transit_gateways = [
                item for item in transit_gateways if item.id in transit_gateway_ids
            ]

        attr_pairs = (
            ("transit-gateway-id", "id"),
            ("state", "state"),
            ("owner-id", "owner_id"),
        )

        result = transit_gateways
        if filters:
            result = filter_resources(transit_gateways, filters, attr_pairs)
        return result

    def delete_transit_gateway(self, transit_gateway_id):
        return self.transit_gateways.pop(transit_gateway_id)

    def modify_transit_gateway(
        self, transit_gateway_id, description=None, options=None
    ):
        transit_gateway = self.transit_gateways.get(transit_gateway_id)
        if description:
            transit_gateway.description = description
        if options:
            transit_gateway.options.update(options)
        return transit_gateway
