from datetime import datetime
from moto.core import get_account_id
from moto.core.utils import iso_8601_datetime_with_milliseconds
from moto.utilities.utils import merge_multiple_dicts, filter_resources
from .core import TaggedEC2Resource
from .vpc_peering_connections import PeeringConnectionStatus
from ..utils import random_transit_gateway_attachment_id, describe_tag_filter


class TransitGatewayAttachment(TaggedEC2Resource):
    def __init__(
        self, backend, resource_id, resource_type, transit_gateway_id, tags=None
    ):
        self.ec2_backend = backend
        self.association = {}
        self.propagation = {}
        self.resource_id = resource_id
        self.resource_type = resource_type

        self.id = random_transit_gateway_attachment_id()
        self.transit_gateway_id = transit_gateway_id

        self.state = "available"
        self.add_tags(tags or {})

        self._created_at = datetime.utcnow()
        self.owner_id = self.resource_owner_id

    @property
    def create_time(self):
        return iso_8601_datetime_with_milliseconds(self._created_at)

    @property
    def resource_owner_id(self):
        return get_account_id()

    @property
    def transit_gateway_owner_id(self):
        return get_account_id()


class TransitGatewayVpcAttachment(TransitGatewayAttachment):
    DEFAULT_OPTIONS = {
        "ApplianceModeSupport": "disable",
        "DnsSupport": "enable",
        "Ipv6Support": "disable",
    }

    def __init__(
        self, backend, transit_gateway_id, vpc_id, subnet_ids, tags=None, options=None
    ):
        super().__init__(
            backend=backend,
            transit_gateway_id=transit_gateway_id,
            resource_id=vpc_id,
            resource_type="vpc",
            tags=tags,
        )

        self.vpc_id = vpc_id
        self.subnet_ids = subnet_ids
        self.options = merge_multiple_dicts(self.DEFAULT_OPTIONS, options or {})


class TransitGatewayPeeringAttachment(TransitGatewayAttachment):
    def __init__(
        self,
        backend,
        transit_gateway_id=None,
        peer_transit_gateway_id=None,
        peer_region=None,
        peer_account_id=None,
        tags=None,
        region_name=None,
    ):
        super().__init__(
            backend=backend,
            transit_gateway_id=transit_gateway_id,
            resource_id=peer_transit_gateway_id,
            resource_type="peering",
            tags=tags,
        )

        self.accepter_tgw_info = {
            "ownerId": peer_account_id,
            "region": peer_region,
            "transitGatewayId": peer_transit_gateway_id,
        }
        self.requester_tgw_info = {
            "ownerId": self.owner_id,
            "region": region_name,
            "transitGatewayId": transit_gateway_id,
        }
        self.status = PeeringConnectionStatus()

    @property
    def resource_owner_id(self):
        return get_account_id()


class TransitGatewayAttachmentBackend(object):
    def __init__(self):
        self.transit_gateway_attachments = {}
        super().__init__()

    def create_transit_gateway_vpn_attachment(
        self, vpn_id, transit_gateway_id, tags=None
    ):
        transit_gateway_vpn_attachment = TransitGatewayAttachment(
            self,
            resource_id=vpn_id,
            resource_type="vpn",
            transit_gateway_id=transit_gateway_id,
            tags=tags,
        )
        self.transit_gateway_attachments[
            transit_gateway_vpn_attachment.id
        ] = transit_gateway_vpn_attachment
        return transit_gateway_vpn_attachment

    def create_transit_gateway_vpc_attachment(
        self, transit_gateway_id, vpc_id, subnet_ids, tags=None, options=None
    ):
        transit_gateway_vpc_attachment = TransitGatewayVpcAttachment(
            self,
            transit_gateway_id=transit_gateway_id,
            tags=tags,
            vpc_id=vpc_id,
            subnet_ids=subnet_ids,
            options=options,
        )
        self.transit_gateway_attachments[
            transit_gateway_vpc_attachment.id
        ] = transit_gateway_vpc_attachment
        return transit_gateway_vpc_attachment

    def describe_transit_gateway_attachments(
        self, transit_gateways_attachment_ids=None, filters=None
    ):
        transit_gateway_attachments = list(self.transit_gateway_attachments.values())

        attr_pairs = (
            ("resource-id", "resource_id"),
            ("resource-type", "resource_type"),
            ("transit-gateway-id", "transit_gateway_id"),
        )

        if (
            not transit_gateways_attachment_ids == []
            and transit_gateways_attachment_ids is not None
        ):
            transit_gateway_attachments = [
                transit_gateways_attachment
                for transit_gateways_attachment in transit_gateway_attachments
                if transit_gateways_attachment.id in transit_gateways_attachment_ids
            ]

        result = transit_gateway_attachments
        if filters:
            result = filter_resources(transit_gateway_attachments, filters, attr_pairs)
        return result

    def describe_transit_gateway_vpc_attachments(
        self, transit_gateways_attachment_ids=None, filters=None
    ):
        transit_gateway_attachments = list(self.transit_gateway_attachments.values())

        attr_pairs = (
            ("state", "state"),
            ("transit-gateway-attachment-id", "id"),
            ("transit-gateway-id", "transit_gateway_id"),
            ("vpc-id", "resource_id"),
        )

        if (
            not transit_gateways_attachment_ids == []
            and transit_gateways_attachment_ids is not None
        ):
            transit_gateway_attachments = [
                transit_gateways_attachment
                for transit_gateways_attachment in transit_gateway_attachments
                if transit_gateways_attachment.id in transit_gateways_attachment_ids
            ]

        result = transit_gateway_attachments
        if filters:
            result = filter_resources(transit_gateway_attachments, filters, attr_pairs)
        return result

    def delete_transit_gateway_vpc_attachment(self, transit_gateway_attachment_id=None):
        transit_gateway_attachment = self.transit_gateway_attachments.pop(
            transit_gateway_attachment_id
        )
        transit_gateway_attachment.state = "deleted"
        return transit_gateway_attachment

    def modify_transit_gateway_vpc_attachment(
        self,
        add_subnet_ids=None,
        options=None,
        remove_subnet_ids=None,
        transit_gateway_attachment_id=None,
    ):

        tgw_attachment = self.transit_gateway_attachments[transit_gateway_attachment_id]
        if remove_subnet_ids:
            tgw_attachment.subnet_ids = [
                id for id in tgw_attachment.subnet_ids if id not in remove_subnet_ids
            ]

        if options:
            tgw_attachment.options.update(options)

        if add_subnet_ids:
            for subnet_id in add_subnet_ids:
                tgw_attachment.subnet_ids.append(subnet_id)

        return tgw_attachment

    def set_attachment_association(
        self, transit_gateway_attachment_id=None, transit_gateway_route_table_id=None
    ):
        self.transit_gateway_attachments[transit_gateway_attachment_id].association = {
            "state": "associated",
            "transitGatewayRouteTableId": transit_gateway_route_table_id,
        }

    def unset_attachment_association(self, tgw_attach_id):
        self.transit_gateway_attachments.get(tgw_attach_id).association = {}

    def set_attachment_propagation(
        self, transit_gateway_attachment_id=None, transit_gateway_route_table_id=None
    ):
        self.transit_gateway_attachments[transit_gateway_attachment_id].propagation = {
            "state": "enabled",
            "transitGatewayRouteTableId": transit_gateway_route_table_id,
        }

    def unset_attachment_propagation(self, tgw_attach_id):
        self.transit_gateway_attachments.get(tgw_attach_id).propagation = {}

    def disable_attachment_propagation(self, transit_gateway_attachment_id=None):
        self.transit_gateway_attachments[transit_gateway_attachment_id].propagation[
            "state"
        ] = "disabled"

    def create_transit_gateway_peering_attachment(
        self,
        transit_gateway_id,
        peer_transit_gateway_id,
        peer_region,
        peer_account_id,
        tags,
    ):
        transit_gateway_peering_attachment = TransitGatewayPeeringAttachment(
            self,
            transit_gateway_id=transit_gateway_id,
            peer_transit_gateway_id=peer_transit_gateway_id,
            peer_region=peer_region,
            peer_account_id=peer_account_id,
            tags=tags,
            region_name=self.region_name,
        )
        transit_gateway_peering_attachment.status.accept()
        transit_gateway_peering_attachment.state = "available"
        self.transit_gateway_attachments[
            transit_gateway_peering_attachment.id
        ] = transit_gateway_peering_attachment
        return transit_gateway_peering_attachment

    def describe_transit_gateway_peering_attachments(
        self, transit_gateways_attachment_ids=None, filters=None
    ):
        transit_gateway_attachments = list(self.transit_gateway_attachments.values())

        attr_pairs = (
            ("state", "state"),
            ("transit-gateway-attachment-id", "id"),
            ("local-owner-id", "requester_tgw_info", "ownerId"),
            ("remote-owner-id", "accepter_tgw_info", "ownerId"),
        )

        if transit_gateways_attachment_ids:
            transit_gateway_attachments = [
                transit_gateways_attachment
                for transit_gateways_attachment in transit_gateway_attachments
                if transit_gateways_attachment.id in transit_gateways_attachment_ids
            ]

        if filters:
            transit_gateway_attachments = filter_resources(
                transit_gateway_attachments, filters, attr_pairs
            )
            transit_gateway_attachments = describe_tag_filter(
                filters, transit_gateway_attachments
            )
        return transit_gateway_attachments

    def accept_transit_gateway_peering_attachment(self, transit_gateway_attachment_id):
        transit_gateway_attachment = self.transit_gateway_attachments[
            transit_gateway_attachment_id
        ]
        transit_gateway_attachment.state = "available"
        transit_gateway_attachment.status.accept()
        return transit_gateway_attachment

    def reject_transit_gateway_peering_attachment(self, transit_gateway_attachment_id):
        transit_gateway_attachment = self.transit_gateway_attachments[
            transit_gateway_attachment_id
        ]
        transit_gateway_attachment.state = "rejected"
        transit_gateway_attachment.status.reject()
        return transit_gateway_attachment

    def delete_transit_gateway_peering_attachment(self, transit_gateway_attachment_id):
        transit_gateway_attachment = self.transit_gateway_attachments[
            transit_gateway_attachment_id
        ]
        transit_gateway_attachment.state = "deleted"
        transit_gateway_attachment.status.deleted()
        return transit_gateway_attachment
