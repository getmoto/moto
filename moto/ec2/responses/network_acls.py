from moto.core.responses import BaseResponse


class NetworkACLs(BaseResponse):
    def create_network_acl(self):
        raise NotImplementedError('NetworkACLs(AmazonVPC).create_network_acl is not yet implemented')

    def create_network_acl_entry(self):
        raise NotImplementedError('NetworkACLs(AmazonVPC).create_network_acl_entry is not yet implemented')

    def delete_network_acl(self):
        raise NotImplementedError('NetworkACLs(AmazonVPC).delete_network_acl is not yet implemented')

    def delete_network_acl_entry(self):
        raise NotImplementedError('NetworkACLs(AmazonVPC).delete_network_acl_entry is not yet implemented')

    def describe_network_acls(self):
        raise NotImplementedError('NetworkACLs(AmazonVPC).describe_network_acls is not yet implemented')

    def replace_network_acl_association(self):
        raise NotImplementedError('NetworkACLs(AmazonVPC).replace_network_acl_association is not yet implemented')

    def replace_network_acl_entry(self):
        raise NotImplementedError('NetworkACLs(AmazonVPC).replace_network_acl_entry is not yet implemented')
