from moto.core.responses import BaseResponse


class CustomerGateways(BaseResponse):
    def create_customer_gateway(self):
        raise NotImplementedError('CustomerGateways(AmazonVPC).create_customer_gateway is not yet implemented')

    def delete_customer_gateway(self):
        raise NotImplementedError('CustomerGateways(AmazonVPC).delete_customer_gateway is not yet implemented')

    def describe_customer_gateways(self):
        raise NotImplementedError('CustomerGateways(AmazonVPC).describe_customer_gateways is not yet implemented')
