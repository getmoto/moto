from moto.core.responses import BaseResponse


class VirtualPrivateGateways(BaseResponse):
    def attach_vpn_gateway(self):
        raise NotImplementedError('VirtualPrivateGateways(AmazonVPC).attach_vpn_gateway is not yet implemented')

    def create_vpn_gateway(self):
        raise NotImplementedError('VirtualPrivateGateways(AmazonVPC).create_vpn_gateway is not yet implemented')

    def delete_vpn_gateway(self):
        raise NotImplementedError('VirtualPrivateGateways(AmazonVPC).delete_vpn_gateway is not yet implemented')

    def describe_vpn_gateways(self):
        raise NotImplementedError('VirtualPrivateGateways(AmazonVPC).describe_vpn_gateways is not yet implemented')

    def detach_vpn_gateway(self):
        raise NotImplementedError('VirtualPrivateGateways(AmazonVPC).detach_vpn_gateway is not yet implemented')
