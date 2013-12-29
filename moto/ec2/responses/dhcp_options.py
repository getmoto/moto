from moto.core.responses import BaseResponse


class DHCPOptions(BaseResponse):
    def associate_dhcp_options(self):
        raise NotImplementedError('DHCPOptions(AmazonVPC).associate_dhcp_options is not yet implemented')

    def create_dhcp_options(self):
        raise NotImplementedError('DHCPOptions(AmazonVPC).create_dhcp_options is not yet implemented')

    def delete_dhcp_options(self):
        raise NotImplementedError('DHCPOptions(AmazonVPC).delete_dhcp_options is not yet implemented')

    def describe_dhcp_options(self):
        raise NotImplementedError('DHCPOptions(AmazonVPC).describe_dhcp_options is not yet implemented')
