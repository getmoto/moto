from moto.core import get_account_id
from moto.utilities.utils import filter_resources

from .core import TaggedEC2Resource
from ..exceptions import InvalidCarrierGatewayID, InvalidVPCIdError
from ..utils import random_carrier_gateway_id


class CarrierGateway(TaggedEC2Resource):
    def __init__(self, ec2_backend, vpc_id, tags=None):
        self.id = random_carrier_gateway_id()
        self.ec2_backend = ec2_backend
        self.vpc_id = vpc_id
        self.state = "available"
        self.add_tags(tags or {})

    @property
    def physical_resource_id(self):
        return self.id

    @property
    def owner_id(self):
        return get_account_id()


class CarrierGatewayBackend:
    def __init__(self):
        self.carrier_gateways = {}

    def create_carrier_gateway(self, vpc_id, tags=None):
        vpc = self.get_vpc(vpc_id)
        if not vpc:
            raise InvalidVPCIdError(vpc_id)
        carrier_gateway = CarrierGateway(self, vpc_id, tags)
        self.carrier_gateways[carrier_gateway.id] = carrier_gateway
        return carrier_gateway

    def delete_carrier_gateway(self, gateway_id):
        if not self.carrier_gateways.get(gateway_id):
            raise InvalidCarrierGatewayID(gateway_id)
        carrier_gateway = self.carrier_gateways.pop(gateway_id)
        carrier_gateway.state = "deleted"
        return carrier_gateway

    def describe_carrier_gateways(self, ids=None, filters=None):
        carrier_gateways = list(self.carrier_gateways.values())

        if ids:
            carrier_gateways = [
                carrier_gateway
                for carrier_gateway in carrier_gateways
                if carrier_gateway.id in ids
            ]

        attr_pairs = (
            ("carrier-gateway-id", "id"),
            ("state", "state"),
            ("vpc-id", "vpc_id"),
            ("owner-id", "owner_id"),
        )

        result = carrier_gateways
        if filters:
            result = filter_resources(carrier_gateways, filters, attr_pairs)
        return result
