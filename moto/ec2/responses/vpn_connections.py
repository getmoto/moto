from moto.core.responses import BaseResponse


class VPNConnections(BaseResponse):
    def create_vpn_connection(self):
        raise NotImplementedError('VPNConnections(AmazonVPC).create_vpn_connection is not yet implemented')

    def delete_vpn_connection(self):
        raise NotImplementedError('VPNConnections(AmazonVPC).delete_vpn_connection is not yet implemented')

    def describe_vpn_connections(self):
        raise NotImplementedError('VPNConnections(AmazonVPC).describe_vpn_connections is not yet implemented')
