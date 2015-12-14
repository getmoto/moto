from __future__ import unicode_literals
from moto.core.exceptions import RESTError


class EC2ClientError(RESTError):
    code = 400


class DependencyViolationError(EC2ClientError):
    def __init__(self, message):
        super(DependencyViolationError, self).__init__(
            "DependencyViolation", message)


class MissingParameterError(EC2ClientError):
    def __init__(self, parameter):
        super(MissingParameterError, self).__init__(
            "MissingParameter",
            "The request must contain the parameter {0}"
            .format(parameter))


class InvalidDHCPOptionsIdError(EC2ClientError):
    def __init__(self, dhcp_options_id):
        super(InvalidDHCPOptionsIdError, self).__init__(
            "InvalidDhcpOptionID.NotFound",
            "DhcpOptionID {0} does not exist."
            .format(dhcp_options_id))


class MalformedDHCPOptionsIdError(EC2ClientError):
    def __init__(self, dhcp_options_id):
        super(MalformedDHCPOptionsIdError, self).__init__(
            "InvalidDhcpOptionsId.Malformed",
            "Invalid id: \"{0}\" (expecting \"dopt-...\")"
            .format(dhcp_options_id))


class InvalidKeyPairNameError(EC2ClientError):
    def __init__(self, key):
        super(InvalidKeyPairNameError, self).__init__(
            "InvalidKeyPair.NotFound",
            "The keypair '{0}' does not exist."
            .format(key))


class InvalidKeyPairDuplicateError(EC2ClientError):
    def __init__(self, key):
        super(InvalidKeyPairDuplicateError, self).__init__(
            "InvalidKeyPair.Duplicate",
            "The keypair '{0}' already exists."
            .format(key))


class InvalidVPCIdError(EC2ClientError):
    def __init__(self, vpc_id):
        super(InvalidVPCIdError, self).__init__(
            "InvalidVpcID.NotFound",
            "VpcID {0} does not exist."
            .format(vpc_id))


class InvalidSubnetIdError(EC2ClientError):
    def __init__(self, subnet_id):
        super(InvalidSubnetIdError, self).__init__(
            "InvalidSubnetID.NotFound",
            "The subnet ID '{0}' does not exist"
            .format(subnet_id))


class InvalidNetworkAclIdError(EC2ClientError):
    def __init__(self, network_acl_id):
        super(InvalidNetworkAclIdError, self).__init__(
            "InvalidNetworkAclID.NotFound",
            "The network acl ID '{0}' does not exist"
            .format(network_acl_id))


class InvalidVpnGatewayIdError(EC2ClientError):
    def __init__(self, network_acl_id):
        super(InvalidVpnGatewayIdError, self).__init__(
            "InvalidVpnGatewayID.NotFound",
            "The virtual private gateway ID '{0}' does not exist"
            .format(network_acl_id))


class InvalidCustomerGatewayIdError(EC2ClientError):
    def __init__(self, customer_gateway_id):
        super(InvalidCustomerGatewayIdError, self).__init__(
            "InvalidCustomerGatewayID.NotFound",
            "The customer gateway ID '{0}' does not exist"
            .format(customer_gateway_id))


class InvalidNetworkInterfaceIdError(EC2ClientError):
    def __init__(self, eni_id):
        super(InvalidNetworkInterfaceIdError, self).__init__(
            "InvalidNetworkInterfaceID.NotFound",
            "The network interface ID '{0}' does not exist"
            .format(eni_id))


class InvalidNetworkAttachmentIdError(EC2ClientError):
    def __init__(self, attachment_id):
        super(InvalidNetworkAttachmentIdError, self).__init__(
            "InvalidAttachmentID.NotFound",
            "The network interface attachment ID '{0}' does not exist"
            .format(attachment_id))


class InvalidSecurityGroupDuplicateError(EC2ClientError):
    def __init__(self, name):
        super(InvalidSecurityGroupDuplicateError, self).__init__(
            "InvalidGroup.Duplicate",
            "The security group '{0}' already exists"
            .format(name))


class InvalidSecurityGroupNotFoundError(EC2ClientError):
    def __init__(self, name):
        super(InvalidSecurityGroupNotFoundError, self).__init__(
            "InvalidGroup.NotFound",
            "The security group '{0}' does not exist"
            .format(name))


class InvalidPermissionNotFoundError(EC2ClientError):
    def __init__(self):
        super(InvalidPermissionNotFoundError, self).__init__(
            "InvalidPermission.NotFound",
            "Could not find a matching ingress rule")


class InvalidRouteTableIdError(EC2ClientError):
    def __init__(self, route_table_id):
        super(InvalidRouteTableIdError, self).__init__(
            "InvalidRouteTableID.NotFound",
            "The routeTable ID '{0}' does not exist"
            .format(route_table_id))


class InvalidRouteError(EC2ClientError):
    def __init__(self, route_table_id, cidr):
        super(InvalidRouteError, self).__init__(
            "InvalidRoute.NotFound",
            "no route with destination-cidr-block {0} in route table {1}"
            .format(cidr, route_table_id))


class InvalidInstanceIdError(EC2ClientError):
    def __init__(self, instance_id):
        super(InvalidInstanceIdError, self).__init__(
            "InvalidInstanceID.NotFound",
            "The instance ID '{0}' does not exist"
            .format(instance_id))


class InvalidAMIIdError(EC2ClientError):
    def __init__(self, ami_id):
        super(InvalidAMIIdError, self).__init__(
            "InvalidAMIID.NotFound",
            "The image id '[{0}]' does not exist"
            .format(ami_id))


class InvalidAMIAttributeItemValueError(EC2ClientError):
    def __init__(self, attribute, value):
        super(InvalidAMIAttributeItemValueError, self).__init__(
            "InvalidAMIAttributeItemValue",
            "Invalid attribute item value \"{0}\" for {1} item type."
            .format(value, attribute))


class MalformedAMIIdError(EC2ClientError):
    def __init__(self, ami_id):
        super(MalformedAMIIdError, self).__init__(
            "InvalidAMIID.Malformed",
            "Invalid id: \"{0}\" (expecting \"ami-...\")"
            .format(ami_id))


class InvalidSnapshotIdError(EC2ClientError):
    def __init__(self, snapshot_id):
        super(InvalidSnapshotIdError, self).__init__(
            "InvalidSnapshot.NotFound",
            "")  # Note: AWS returns empty message for this, as of 2014.08.22.


class InvalidVolumeIdError(EC2ClientError):
    def __init__(self, volume_id):
        super(InvalidVolumeIdError, self).__init__(
            "InvalidVolume.NotFound",
            "The volume '{0}' does not exist."
            .format(volume_id))


class InvalidVolumeAttachmentError(EC2ClientError):
    def __init__(self, volume_id, instance_id):
        super(InvalidVolumeAttachmentError, self).__init__(
            "InvalidAttachment.NotFound",
            "Volume {0} can not be detached from {1} because it is not attached"
            .format(volume_id, instance_id))


class InvalidDomainError(EC2ClientError):
    def __init__(self, domain):
        super(InvalidDomainError, self).__init__(
            "InvalidParameterValue",
            "Invalid value '{0}' for domain."
            .format(domain))


class InvalidAddressError(EC2ClientError):
    def __init__(self, ip):
        super(InvalidAddressError, self).__init__(
            "InvalidAddress.NotFound",
            "Address '{0}' not found."
            .format(ip))


class InvalidAllocationIdError(EC2ClientError):
    def __init__(self, allocation_id):
        super(InvalidAllocationIdError, self).__init__(
            "InvalidAllocationID.NotFound",
            "Allocation ID '{0}' not found."
            .format(allocation_id))


class InvalidAssociationIdError(EC2ClientError):
    def __init__(self, association_id):
        super(InvalidAssociationIdError, self).__init__(
            "InvalidAssociationID.NotFound",
            "Association ID '{0}' not found."
            .format(association_id))


class InvalidVPCPeeringConnectionIdError(EC2ClientError):
    def __init__(self, vpc_peering_connection_id):
        super(InvalidVPCPeeringConnectionIdError, self).__init__(
            "InvalidVpcPeeringConnectionId.NotFound",
            "VpcPeeringConnectionID {0} does not exist."
            .format(vpc_peering_connection_id))


class InvalidVPCPeeringConnectionStateTransitionError(EC2ClientError):
    def __init__(self, vpc_peering_connection_id):
        super(InvalidVPCPeeringConnectionStateTransitionError, self).__init__(
            "InvalidStateTransition",
            "VpcPeeringConnectionID {0} is not in the correct state for the request."
            .format(vpc_peering_connection_id))


class InvalidParameterValueError(EC2ClientError):
    def __init__(self, parameter_value):
        super(InvalidParameterValueError, self).__init__(
            "InvalidParameterValue",
            "Value {0} is invalid for parameter."
            .format(parameter_value))


class InvalidParameterValueErrorTagNull(EC2ClientError):
    def __init__(self):
        super(InvalidParameterValueErrorTagNull, self).__init__(
            "InvalidParameterValue",
            "Tag value cannot be null. Use empty string instead.")


class InvalidInternetGatewayIdError(EC2ClientError):
    def __init__(self, internet_gateway_id):
        super(InvalidInternetGatewayIdError, self).__init__(
            "InvalidInternetGatewayID.NotFound",
            "InternetGatewayID {0} does not exist."
            .format(internet_gateway_id))


class GatewayNotAttachedError(EC2ClientError):
    def __init__(self, internet_gateway_id, vpc_id):
        super(GatewayNotAttachedError, self).__init__(
            "Gateway.NotAttached",
            "InternetGatewayID {0} is not attached to a VPC {1}."
            .format(internet_gateway_id, vpc_id))


class ResourceAlreadyAssociatedError(EC2ClientError):
    def __init__(self, resource_id):
        super(ResourceAlreadyAssociatedError, self).__init__(
            "Resource.AlreadyAssociated",
            "Resource {0} is already associated."
            .format(resource_id))


class TagLimitExceeded(EC2ClientError):
    def __init__(self):
        super(TagLimitExceeded, self).__init__(
            "TagLimitExceeded",
            "The maximum number of Tags for a resource has been reached.")


class InvalidID(EC2ClientError):
    def __init__(self, resource_id):
        super(InvalidID, self).__init__(
            "InvalidID",
            "The ID '{0}' is not valid"
            .format(resource_id))


class InvalidCIDRSubnetError(EC2ClientError):
    def __init__(self, cidr):
        super(InvalidCIDRSubnetError, self).__init__(
            "InvalidParameterValue",
            "invalid CIDR subnet specification: {0}"
            .format(cidr))
