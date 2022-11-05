from datetime import datetime
from moto.core.utils import iso_8601_datetime_with_milliseconds
from moto.utilities.utils import filter_resources
from .core import TaggedEC2Resource
from ..utils import random_transit_gateway_route_table_id


class TransitGatewayRouteTable(TaggedEC2Resource):
    def __init__(
        self,
        backend,
        transit_gateway_id,
        tags=None,
        default_association_route_table=False,
        default_propagation_route_table=False,
    ):
        self.ec2_backend = backend
        self.id = random_transit_gateway_route_table_id()
        self.transit_gateway_id = transit_gateway_id

        self._created_at = datetime.utcnow()

        self.default_association_route_table = default_association_route_table
        self.default_propagation_route_table = default_propagation_route_table
        self.state = "available"
        self.routes = {}
        self.add_tags(tags or {})
        self.route_table_association = {}
        self.route_table_propagation = {}

    @property
    def physical_resource_id(self):
        return self.id

    @property
    def create_time(self):
        return iso_8601_datetime_with_milliseconds(self._created_at)


class TransitGatewayRouteTableBackend:
    def __init__(self):
        self.transit_gateways_route_tables = {}

    def create_transit_gateway_route_table(
        self,
        transit_gateway_id,
        tags=None,
        default_association_route_table=False,
        default_propagation_route_table=False,
    ):
        transit_gateways_route_table = TransitGatewayRouteTable(
            self,
            transit_gateway_id=transit_gateway_id,
            tags=tags,
            default_association_route_table=default_association_route_table,
            default_propagation_route_table=default_propagation_route_table,
        )
        self.transit_gateways_route_tables[
            transit_gateways_route_table.id
        ] = transit_gateways_route_table
        return transit_gateways_route_table

    def get_all_transit_gateway_route_tables(
        self, transit_gateway_route_table_ids=None, filters=None
    ):
        transit_gateway_route_tables = list(self.transit_gateways_route_tables.values())

        attr_pairs = (
            ("default-association-route-table", "default_association_route_table"),
            ("default-propagation-route-table", "default_propagation_route_table"),
            ("state", "state"),
            ("transit-gateway-id", "transit_gateway_id"),
            ("transit-gateway-route-table-id", "id"),
        )

        if transit_gateway_route_table_ids:
            transit_gateway_route_tables = [
                transit_gateway_route_table
                for transit_gateway_route_table in transit_gateway_route_tables
                if transit_gateway_route_table.id in transit_gateway_route_table_ids
            ]

        result = transit_gateway_route_tables
        if filters:
            result = filter_resources(transit_gateway_route_tables, filters, attr_pairs)
        return result

    def delete_transit_gateway_route_table(self, transit_gateway_route_table_id):
        transit_gateways_route_table = self.transit_gateways_route_tables[
            transit_gateway_route_table_id
        ]
        transit_gateways_route_table.state = "deleted"
        return transit_gateways_route_table

    def create_transit_gateway_route(
        self,
        transit_gateway_route_table_id,
        destination_cidr_block,
        transit_gateway_attachment_id=None,
        blackhole=False,
    ):
        transit_gateways_route_table = self.transit_gateways_route_tables.get(
            transit_gateway_route_table_id
        )
        transit_gateway_attachment = self.transit_gateway_attachments.get(
            transit_gateway_attachment_id
        )
        transit_gateways_route_table.routes[destination_cidr_block] = {
            "destinationCidrBlock": destination_cidr_block,
            "prefixListId": "",
            "state": "blackhole" if blackhole else "active",
            "type": "static",
        }

        if transit_gateway_attachment:
            transit_gateway_attachment_dict = {
                "transitGatewayAttachments": {
                    "resourceId": transit_gateway_attachment.resource_id,
                    "resourceType": transit_gateway_attachment.resource_type,
                    "transitGatewayAttachmentId": transit_gateway_attachment_id,
                }
            }
            transit_gateways_route_table.routes[destination_cidr_block].update(
                transit_gateway_attachment_dict
            )
        return transit_gateways_route_table.routes[destination_cidr_block]

    def delete_transit_gateway_route(
        self, transit_gateway_route_table_id, destination_cidr_block
    ):
        transit_gateways_route_table = self.transit_gateways_route_tables[
            transit_gateway_route_table_id
        ]
        transit_gateways_route_table.routes[destination_cidr_block]["state"] = "deleted"
        return transit_gateways_route_table

    def search_transit_gateway_routes(
        self, transit_gateway_route_table_id, filters, max_results=None
    ):
        """
        The following filters are currently supported: type, state, route-search.exact-match
        """
        transit_gateway_route_table = self.transit_gateways_route_tables.get(
            transit_gateway_route_table_id
        )
        if not transit_gateway_route_table:
            return []

        attr_pairs = (
            ("type", "type"),
            ("state", "state"),
            ("route-search.exact-match", "destinationCidrBlock"),
        )

        routes = transit_gateway_route_table.routes.copy()
        for key in transit_gateway_route_table.routes:
            for attrs in attr_pairs:
                values = filters.get(attrs[0]) or None
                if values:
                    if routes.get(key).get(attrs[1]) not in values:
                        routes.pop(key)
                        break
        if max_results:
            routes = routes[: int(max_results)]
        return routes

    def set_route_table_association(
        self, transit_gateway_attachment_id, transit_gateway_route_table_id
    ):
        self.transit_gateways_route_tables[
            transit_gateway_route_table_id
        ].route_table_association = {
            "resourceId": self.transit_gateway_attachments[
                transit_gateway_attachment_id
            ].resource_id,
            "resourceType": self.transit_gateway_attachments[
                transit_gateway_attachment_id
            ].resource_type,
            "state": "associated",
            "transitGatewayAttachmentId": transit_gateway_attachment_id,
        }

    def unset_route_table_association(self, tgw_rt_id):
        tgw_rt = self.transit_gateways_route_tables[tgw_rt_id]
        tgw_rt.route_table_association = {}

    def set_route_table_propagation(
        self, transit_gateway_attachment_id, transit_gateway_route_table_id
    ):
        self.transit_gateways_route_tables[
            transit_gateway_route_table_id
        ].route_table_propagation = {
            "resourceId": self.transit_gateway_attachments[
                transit_gateway_attachment_id
            ].resource_id,
            "resourceType": self.transit_gateway_attachments[
                transit_gateway_attachment_id
            ].resource_type,
            "state": "enabled",
            "transitGatewayAttachmentId": transit_gateway_attachment_id,
        }

    def unset_route_table_propagation(self, tgw_rt_id):
        tgw_rt = self.transit_gateways_route_tables[tgw_rt_id]
        tgw_rt.route_table_propagation = {}

    def disable_route_table_propagation(self, transit_gateway_route_table_id):
        self.transit_gateways_route_tables[
            transit_gateway_route_table_id
        ].route_table_propagation = {}

    def get_all_transit_gateway_route_table_associations(
        self, transit_gateway_route_table_id=None, filters=None
    ):
        transit_gateway_route_tables = list(self.transit_gateways_route_tables.values())

        if transit_gateway_route_tables:
            transit_gateway_route_tables = [
                transit_gateway_route_table
                for transit_gateway_route_table in transit_gateway_route_tables
                if transit_gateway_route_table.id in transit_gateway_route_table_id
            ]

        attr_pairs = (
            ("resource-id", "route_table_association", "resourceId"),
            ("resource-type", "route_table_association", "resourceType"),
            (
                "transit-gateway-attachment-id",
                "route_table_association",
                "transitGatewayAttachmentId",
            ),
        )

        result = transit_gateway_route_tables
        if filters:
            result = filter_resources(transit_gateway_route_tables, filters, attr_pairs)
        return result

    def get_all_transit_gateway_route_table_propagations(
        self, transit_gateway_route_table_id=None, filters=None
    ):
        transit_gateway_route_tables = list(self.transit_gateways_route_tables.values())

        if transit_gateway_route_tables:
            transit_gateway_route_tables = [
                transit_gateway_route_table
                for transit_gateway_route_table in transit_gateway_route_tables
                if transit_gateway_route_table.id in transit_gateway_route_table_id
            ]

        attr_pairs = (
            ("resource-id", "route_table_propagation", "resourceId"),
            ("resource-type", "route_table_propagation", "resourceType"),
            (
                "transit-gateway-attachment-id",
                "route_table_propagation",
                "transitGatewayAttachmentId",
            ),
        )

        result = transit_gateway_route_tables
        if filters:
            result = filter_resources(transit_gateway_route_tables, filters, attr_pairs)
        return result


class TransitGatewayRelations(object):
    # this class is for TransitGatewayAssociation and TransitGatewayPropagation
    def __init__(
        self,
        backend,
        transit_gateway_attachment_id=None,
        transit_gateway_route_table_id=None,
        state=None,
    ):
        self.ec2_backend = backend
        self.transit_gateway_attachment_id = transit_gateway_attachment_id
        self.transit_gateway_route_table_id = transit_gateway_route_table_id
        self.resource_id = backend.transit_gateway_attachments[
            transit_gateway_attachment_id
        ].resource_id
        self.resource_type = backend.transit_gateway_attachments[
            transit_gateway_attachment_id
        ].resource_type
        self.state = state


class TransitGatewayRelationsBackend:
    def __init__(self):
        self.transit_gateway_associations = {}
        self.transit_gateway_propagations = {}

    def associate_transit_gateway_route_table(
        self, transit_gateway_attachment_id=None, transit_gateway_route_table_id=None
    ):
        transit_gateway_association = TransitGatewayRelations(
            self,
            transit_gateway_attachment_id,
            transit_gateway_route_table_id,
            state="associated",
        )
        self.set_route_table_association(
            transit_gateway_attachment_id, transit_gateway_route_table_id
        )
        self.set_attachment_association(
            transit_gateway_attachment_id, transit_gateway_route_table_id
        )
        self.transit_gateway_associations[
            transit_gateway_attachment_id
        ] = transit_gateway_association

        return transit_gateway_association

    def enable_transit_gateway_route_table_propagation(
        self, transit_gateway_attachment_id=None, transit_gateway_route_table_id=None
    ):
        transit_gateway_propagation = TransitGatewayRelations(
            self,
            transit_gateway_attachment_id,
            transit_gateway_route_table_id,
            state="enabled",
        )
        self.set_route_table_propagation(
            transit_gateway_attachment_id, transit_gateway_route_table_id
        )
        self.set_attachment_propagation(
            transit_gateway_attachment_id, transit_gateway_route_table_id
        )
        self.transit_gateway_propagations[
            transit_gateway_attachment_id
        ] = transit_gateway_propagation

        return transit_gateway_propagation

    def disable_transit_gateway_route_table_propagation(
        self, transit_gateway_attachment_id=None, transit_gateway_route_table_id=None
    ):
        self.disable_route_table_propagation(
            transit_gateway_route_table_id=transit_gateway_route_table_id
        )
        self.disable_attachment_propagation(
            transit_gateway_attachment_id=transit_gateway_attachment_id
        )
        self.transit_gateway_propagations[
            transit_gateway_attachment_id
        ].state = "disabled"
        transit_gateway_propagation = self.transit_gateway_propagations.pop(
            transit_gateway_attachment_id
        )

        return transit_gateway_propagation

    def disassociate_transit_gateway_route_table(self, tgw_attach_id, tgw_rt_id):
        tgw_association = self.transit_gateway_associations.pop(tgw_attach_id)
        tgw_association.state = "disassociated"

        self.unset_route_table_association(tgw_rt_id)
        self.unset_attachment_association(tgw_attach_id)

        return tgw_association
