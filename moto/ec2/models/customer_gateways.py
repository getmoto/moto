from .core import TaggedEC2Resource
from ..exceptions import InvalidCustomerGatewayIdError
from ..utils import random_customer_gateway_id


class CustomerGateway(TaggedEC2Resource):
    def __init__(
        self,
        ec2_backend,
        gateway_id,
        gateway_type,
        ip_address,
        bgp_asn,
        state="available",
        tags=None,
    ):
        self.ec2_backend = ec2_backend
        self.id = gateway_id
        self.type = gateway_type
        self.ip_address = ip_address
        self.bgp_asn = bgp_asn
        self.attachments = {}
        self.state = state
        self.add_tags(tags or {})
        super().__init__()

    def get_filter_value(self, filter_name):
        return super().get_filter_value(filter_name, "DescribeCustomerGateways")


class CustomerGatewayBackend(object):
    def __init__(self):
        self.customer_gateways = {}
        super().__init__()

    def create_customer_gateway(
        self, gateway_type="ipsec.1", ip_address=None, bgp_asn=None, tags=None
    ):
        customer_gateway_id = random_customer_gateway_id()
        customer_gateway = CustomerGateway(
            self, customer_gateway_id, gateway_type, ip_address, bgp_asn, tags=tags
        )
        self.customer_gateways[customer_gateway_id] = customer_gateway
        return customer_gateway

    def get_all_customer_gateways(self, filters=None, customer_gateway_ids=None):
        customer_gateways = self.customer_gateways.copy().values()
        if customer_gateway_ids:
            customer_gateways = [
                cg for cg in customer_gateways if cg.id in customer_gateway_ids
            ]

        if filters is not None:
            if filters.get("customer-gateway-id") is not None:
                customer_gateways = [
                    customer_gateway
                    for customer_gateway in customer_gateways
                    if customer_gateway.id in filters["customer-gateway-id"]
                ]
            if filters.get("type") is not None:
                customer_gateways = [
                    customer_gateway
                    for customer_gateway in customer_gateways
                    if customer_gateway.type in filters["type"]
                ]
            if filters.get("bgp-asn") is not None:
                customer_gateways = [
                    customer_gateway
                    for customer_gateway in customer_gateways
                    if customer_gateway.bgp_asn in filters["bgp-asn"]
                ]
            if filters.get("ip-address") is not None:
                customer_gateways = [
                    customer_gateway
                    for customer_gateway in customer_gateways
                    if customer_gateway.ip_address in filters["ip-address"]
                ]
        return customer_gateways

    def get_customer_gateway(self, customer_gateway_id):
        customer_gateway = self.customer_gateways.get(customer_gateway_id, None)
        if not customer_gateway:
            raise InvalidCustomerGatewayIdError(customer_gateway_id)
        return customer_gateway

    def delete_customer_gateway(self, customer_gateway_id):
        customer_gateway = self.get_customer_gateway(customer_gateway_id)
        customer_gateway.state = "deleted"
        # deleted = self.customer_gateways.pop(customer_gateway_id, None)
        deleted = True
        if not deleted:
            raise InvalidCustomerGatewayIdError(customer_gateway_id)
        return deleted
