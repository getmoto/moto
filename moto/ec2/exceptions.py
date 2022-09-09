from moto.core.exceptions import RESTError


# EC2 has a custom root-tag - <Response> vs <ErrorResponse>
# `terraform destroy` will complain if the roottag is incorrect
# See https://docs.aws.amazon.com/AWSEC2/latest/APIReference/errors-overview.html#api-error-response
EC2_ERROR_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Errors>
    <Error>
      <Code>{{error_type}}</Code>
      <Message>{{message}}</Message>
    </Error>
  </Errors>
  <{{request_id_tag}}>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</{{request_id_tag}}>
</Response>
"""


class EC2ClientError(RESTError):
    code = 400
    # EC2 uses <RequestID> as tag name in the XML response
    request_id_tag_name = "RequestID"

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("template", "custom_response")
        self.templates["custom_response"] = EC2_ERROR_RESPONSE
        super().__init__(*args, **kwargs)


class DefaultVpcAlreadyExists(EC2ClientError):
    def __init__(self):
        super().__init__(
            "DefaultVpcAlreadyExists",
            "A Default VPC already exists for this account in this region.",
        )


class DependencyViolationError(EC2ClientError):
    def __init__(self, message):
        super().__init__("DependencyViolation", message)


class MissingParameterError(EC2ClientError):
    def __init__(self, parameter):
        super().__init__(
            "MissingParameter",
            "The request must contain the parameter {0}".format(parameter),
        )


class InvalidDHCPOptionsIdError(EC2ClientError):
    def __init__(self, dhcp_options_id):
        super().__init__(
            "InvalidDhcpOptionID.NotFound",
            "DhcpOptionID {0} does not exist.".format(dhcp_options_id),
        )


class InvalidRequest(EC2ClientError):
    def __init__(self):
        super().__init__("InvalidRequest", "The request received was invalid")


class InvalidParameterCombination(EC2ClientError):
    def __init__(self, msg):
        super().__init__("InvalidParameterCombination", msg)


class MalformedDHCPOptionsIdError(EC2ClientError):
    def __init__(self, dhcp_options_id):
        super().__init__(
            "InvalidDhcpOptionsId.Malformed",
            'Invalid id: "{0}" (expecting "dopt-...")'.format(dhcp_options_id),
        )


class InvalidKeyPairNameError(EC2ClientError):
    def __init__(self, key):
        super().__init__(
            "InvalidKeyPair.NotFound", "The keypair '{0}' does not exist.".format(key)
        )


class InvalidKeyPairDuplicateError(EC2ClientError):
    def __init__(self, key):
        super().__init__(
            "InvalidKeyPair.Duplicate", "The keypair '{0}' already exists.".format(key)
        )


class InvalidKeyPairFormatError(EC2ClientError):
    def __init__(self):
        super().__init__(
            "InvalidKeyPair.Format", "Key is not in valid OpenSSH public key format"
        )


class InvalidVPCIdError(EC2ClientError):
    def __init__(self, vpc_id):

        super().__init__(
            "InvalidVpcID.NotFound", "VpcID {0} does not exist.".format(vpc_id)
        )


class InvalidSubnetIdError(EC2ClientError):
    def __init__(self, subnet_id):
        super().__init__(
            "InvalidSubnetID.NotFound",
            "The subnet ID '{}' does not exist".format(subnet_id),
        )


class InvalidFlowLogIdError(EC2ClientError):
    def __init__(self, count, flow_log_ids):
        super().__init__(
            "InvalidFlowLogId.NotFound",
            "These flow log ids in the input list are not found: [TotalCount: {0}] {1}".format(
                count, flow_log_ids
            ),
        )


class FlowLogAlreadyExists(EC2ClientError):
    def __init__(self):
        super().__init__(
            "FlowLogAlreadyExists",
            "Error. There is an existing Flow Log with the same configuration and log destination.",
        )


class InvalidNetworkAclIdError(EC2ClientError):
    def __init__(self, network_acl_id):
        super().__init__(
            "InvalidNetworkAclID.NotFound",
            "The network acl ID '{0}' does not exist".format(network_acl_id),
        )


class InvalidVpnGatewayIdError(EC2ClientError):
    def __init__(self, vpn_gw):
        super().__init__(
            "InvalidVpnGatewayID.NotFound",
            "The virtual private gateway ID '{0}' does not exist".format(vpn_gw),
        )


class InvalidVpnGatewayAttachmentError(EC2ClientError):
    def __init__(self, vpn_gw, vpc_id):
        super().__init__(
            "InvalidVpnGatewayAttachment.NotFound",
            "The attachment with vpn gateway ID '{}' and vpc ID '{}' does not exist".format(
                vpn_gw, vpc_id
            ),
        )


class InvalidVpnConnectionIdError(EC2ClientError):
    def __init__(self, network_acl_id):
        super().__init__(
            "InvalidVpnConnectionID.NotFound",
            "The vpnConnection ID '{0}' does not exist".format(network_acl_id),
        )


class InvalidCustomerGatewayIdError(EC2ClientError):
    def __init__(self, customer_gateway_id):
        super().__init__(
            "InvalidCustomerGatewayID.NotFound",
            "The customer gateway ID '{0}' does not exist".format(customer_gateway_id),
        )


class InvalidNetworkInterfaceIdError(EC2ClientError):
    def __init__(self, eni_id):
        super().__init__(
            "InvalidNetworkInterfaceID.NotFound",
            "The network interface ID '{0}' does not exist".format(eni_id),
        )


class InvalidNetworkAttachmentIdError(EC2ClientError):
    def __init__(self, attachment_id):
        super().__init__(
            "InvalidAttachmentID.NotFound",
            "The network interface attachment ID '{0}' does not exist".format(
                attachment_id
            ),
        )


class InvalidSecurityGroupDuplicateError(EC2ClientError):
    def __init__(self, name):
        super().__init__(
            "InvalidGroup.Duplicate",
            "The security group '{0}' already exists".format(name),
        )


class InvalidSecurityGroupNotFoundError(EC2ClientError):
    def __init__(self, name):
        super().__init__(
            "InvalidGroup.NotFound",
            "The security group '{0}' does not exist".format(name),
        )


class InvalidPermissionNotFoundError(EC2ClientError):
    def __init__(self):
        super().__init__(
            "InvalidPermission.NotFound",
            "The specified rule does not exist in this security group",
        )


class InvalidPermissionDuplicateError(EC2ClientError):
    def __init__(self):
        super().__init__(
            "InvalidPermission.Duplicate", "The specified rule already exists"
        )


class InvalidRouteTableIdError(EC2ClientError):
    def __init__(self, route_table_id):
        super().__init__(
            "InvalidRouteTableID.NotFound",
            "The routeTable ID '{0}' does not exist".format(route_table_id),
        )


class InvalidRouteError(EC2ClientError):
    def __init__(self, route_table_id, cidr):
        super().__init__(
            "InvalidRoute.NotFound",
            "no route with destination-cidr-block {0} in route table {1}".format(
                cidr, route_table_id
            ),
        )


class RouteAlreadyExistsError(EC2ClientError):
    def __init__(self, cidr):
        super().__init__(
            "RouteAlreadyExists",
            "The route identified by {0} already exists".format(cidr),
        )


class InvalidInstanceIdError(EC2ClientError):
    def __init__(self, instance_id):
        if isinstance(instance_id, str):
            instance_id = [instance_id]
        if len(instance_id) > 1:
            msg = f"The instance IDs '{', '.join(instance_id)}' do not exist"
        else:
            msg = f"The instance ID '{instance_id[0]}' does not exist"
        super().__init__("InvalidInstanceID.NotFound", msg)


class InvalidInstanceTypeError(EC2ClientError):
    def __init__(self, instance_type):
        super().__init__(
            "InvalidInstanceType.NotFound",
            "The instance type '{0}' does not exist".format(instance_type),
        )


class InvalidAMIIdError(EC2ClientError):
    def __init__(self, ami_id):
        super().__init__(
            "InvalidAMIID.NotFound",
            "The image id '[{0}]' does not exist".format(ami_id),
        )


class UnvailableAMIIdError(EC2ClientError):
    def __init__(self, ami_id):
        super().__init__(
            "InvalidAMIID.Unavailable",
            "The image id '[{0}]' is no longer available".format(ami_id),
        )


class InvalidAMIAttributeItemValueError(EC2ClientError):
    def __init__(self, attribute, value):
        super().__init__(
            "InvalidAMIAttributeItemValue",
            'Invalid attribute item value "{0}" for {1} item type.'.format(
                value, attribute
            ),
        )


class MalformedAMIIdError(EC2ClientError):
    def __init__(self, ami_id):
        super().__init__(
            "InvalidAMIID.Malformed",
            'Invalid id: "{0}" (expecting "ami-...")'.format(ami_id),
        )


class InvalidSnapshotIdError(EC2ClientError):
    def __init__(self):
        # Note: AWS returns empty message for this, as of 2014.08.22.
        super().__init__("InvalidSnapshot.NotFound", "")


class InvalidSnapshotInUse(EC2ClientError):
    def __init__(self, snapshot_id, ami_id):
        super().__init__(
            "InvalidSnapshot.InUse",
            f"The snapshot {snapshot_id} is currently in use by {ami_id}",
        )


class InvalidVolumeIdError(EC2ClientError):
    def __init__(self, volume_id):
        super().__init__(
            "InvalidVolume.NotFound",
            "The volume '{0}' does not exist.".format(volume_id),
        )


class InvalidVolumeAttachmentError(EC2ClientError):
    def __init__(self, volume_id, instance_id):
        super().__init__(
            "InvalidAttachment.NotFound",
            "Volume {0} can not be detached from {1} because it is not attached".format(
                volume_id, instance_id
            ),
        )


class InvalidVolumeDetachmentError(EC2ClientError):
    def __init__(self, volume_id, instance_id, device):
        super().__init__(
            "InvalidAttachment.NotFound",
            "The volume {0} is not attached to instance {1} as device {2}".format(
                volume_id, instance_id, device
            ),
        )


class VolumeInUseError(EC2ClientError):
    def __init__(self, volume_id, instance_id):
        super().__init__(
            "VolumeInUse",
            "Volume {0} is currently attached to {1}".format(volume_id, instance_id),
        )


class InvalidDomainError(EC2ClientError):
    def __init__(self, domain):
        super().__init__(
            "InvalidParameterValue", "Invalid value '{0}' for domain.".format(domain)
        )


class InvalidAddressError(EC2ClientError):
    def __init__(self, ip):
        super().__init__(
            "InvalidAddress.NotFound", "Address '{0}' not found.".format(ip)
        )


class LogDestinationNotFoundError(EC2ClientError):
    def __init__(self, bucket_name):
        super().__init__(
            "LogDestinationNotFoundException",
            "LogDestination: '{0}' does not exist.".format(bucket_name),
        )


class InvalidAllocationIdError(EC2ClientError):
    def __init__(self, allocation_id):
        super().__init__(
            "InvalidAllocationID.NotFound",
            "Allocation ID '{0}' not found.".format(allocation_id),
        )


class InvalidAssociationIdError(EC2ClientError):
    def __init__(self, association_id):
        super().__init__(
            "InvalidAssociationID.NotFound",
            "Association ID '{0}' not found.".format(association_id),
        )


class InvalidVpcCidrBlockAssociationIdError(EC2ClientError):
    def __init__(self, association_id):
        super().__init__(
            "InvalidVpcCidrBlockAssociationIdError.NotFound",
            "The vpc CIDR block association ID '{0}' does not exist".format(
                association_id
            ),
        )


class InvalidVPCPeeringConnectionIdError(EC2ClientError):
    def __init__(self, vpc_peering_connection_id):
        super().__init__(
            "InvalidVpcPeeringConnectionId.NotFound",
            "VpcPeeringConnectionID {0} does not exist.".format(
                vpc_peering_connection_id
            ),
        )


class InvalidVPCPeeringConnectionStateTransitionError(EC2ClientError):
    def __init__(self, vpc_peering_connection_id):
        super().__init__(
            "InvalidStateTransition",
            "VpcPeeringConnectionID {0} is not in the correct state for the request.".format(
                vpc_peering_connection_id
            ),
        )


class InvalidServiceName(EC2ClientError):
    def __init__(self, service_name):
        super().__init__(
            "InvalidServiceName",
            f"The Vpc Endpoint Service '{service_name}' does not exist",
        )


class InvalidFilter(EC2ClientError):
    def __init__(self, filter_name):
        super().__init__("InvalidFilter", f"The filter '{filter_name}' is invalid")


class InvalidNextToken(EC2ClientError):
    def __init__(self, next_token):
        super().__init__("InvalidNextToken", f"The token '{next_token}' is invalid")


class InvalidDependantParameterError(EC2ClientError):
    def __init__(self, dependant_parameter, parameter, parameter_value):
        super().__init__(
            "InvalidParameter",
            "{0} can't be empty if {1} is {2}.".format(
                dependant_parameter, parameter, parameter_value
            ),
        )


class InvalidDependantParameterTypeError(EC2ClientError):
    def __init__(self, dependant_parameter, parameter_value, parameter):
        super().__init__(
            "InvalidParameter",
            "{0} type must be {1} if {2} is provided.".format(
                dependant_parameter, parameter_value, parameter
            ),
        )


class InvalidAggregationIntervalParameterError(EC2ClientError):
    def __init__(self, parameter):
        super().__init__("InvalidParameter", "Invalid {0}".format(parameter))


class InvalidParameterValueError(EC2ClientError):
    def __init__(self, parameter_value):
        super().__init__(
            "InvalidParameterValue",
            "Value {0} is invalid for parameter.".format(parameter_value),
        )


class EmptyTagSpecError(EC2ClientError):
    def __init__(self):
        super().__init__(
            "InvalidParameterValue", "Tag specification must have at least one tag"
        )


class InvalidParameterValueErrorTagNull(EC2ClientError):
    def __init__(self):
        super().__init__(
            "InvalidParameterValue",
            "Tag value cannot be null. Use empty string instead.",
        )


class InvalidParameterValueErrorUnknownAttribute(EC2ClientError):
    def __init__(self, parameter_value):
        super().__init__(
            "InvalidParameterValue",
            "Value ({0}) for parameter attribute is invalid. Unknown attribute.".format(
                parameter_value
            ),
        )


class InvalidGatewayIDError(EC2ClientError):
    def __init__(self, gateway_id):
        super().__init__(
            "InvalidGatewayID.NotFound",
            "The eigw ID '{0}' does not exist".format(gateway_id),
        )


class InvalidInternetGatewayIdError(EC2ClientError):
    def __init__(self, internet_gateway_id):
        super().__init__(
            "InvalidInternetGatewayID.NotFound",
            "InternetGatewayID {0} does not exist.".format(internet_gateway_id),
        )


class GatewayNotAttachedError(EC2ClientError):
    def __init__(self, internet_gateway_id, vpc_id):
        super().__init__(
            "Gateway.NotAttached",
            "InternetGatewayID {0} is not attached to a VPC {1}.".format(
                internet_gateway_id, vpc_id
            ),
        )


class ResourceAlreadyAssociatedError(EC2ClientError):
    def __init__(self, resource_id):
        super().__init__(
            "Resource.AlreadyAssociated",
            "Resource {0} is already associated.".format(resource_id),
        )


class TagLimitExceeded(EC2ClientError):
    def __init__(self):
        super().__init__(
            "TagLimitExceeded",
            "The maximum number of Tags for a resource has been reached.",
        )


class InvalidID(EC2ClientError):
    def __init__(self, resource_id):
        super().__init__("InvalidID", "The ID '{0}' is not valid".format(resource_id))


class InvalidCIDRSubnetError(EC2ClientError):
    def __init__(self, cidr):
        super().__init__(
            "InvalidParameterValue",
            "invalid CIDR subnet specification: {0}".format(cidr),
        )


class RulesPerSecurityGroupLimitExceededError(EC2ClientError):
    def __init__(self):
        super().__init__(
            "RulesPerSecurityGroupLimitExceeded",
            "The maximum number of rules per security group " "has been reached.",
        )


class MotoNotImplementedError(NotImplementedError):
    def __init__(self, blurb):
        super().__init__(
            "{0} has not been implemented in Moto yet."
            " Feel free to open an issue at"
            " https://github.com/spulec/moto/issues".format(blurb)
        )


class FilterNotImplementedError(MotoNotImplementedError):
    def __init__(self, filter_name, method_name):
        super().__init__("The filter '{0}' for {1}".format(filter_name, method_name))


class CidrLimitExceeded(EC2ClientError):
    def __init__(self, vpc_id, max_cidr_limit):
        super().__init__(
            "CidrLimitExceeded",
            "This network '{0}' has met its maximum number of allowed CIDRs: {1}".format(
                vpc_id, max_cidr_limit
            ),
        )


class UnsupportedTenancy(EC2ClientError):
    def __init__(self, tenancy):
        super().__init__(
            "UnsupportedTenancy",
            "The tenancy value {0} is not supported.".format(tenancy),
        )


class OperationNotPermitted(EC2ClientError):
    def __init__(self, association_id):
        super().__init__(
            "OperationNotPermitted",
            "The vpc CIDR block with association ID {} may not be disassociated. "
            "It is the primary IPv4 CIDR block of the VPC".format(association_id),
        )


class InvalidAvailabilityZoneError(EC2ClientError):
    def __init__(self, availability_zone_value, valid_availability_zones):
        super().__init__(
            "InvalidParameterValue",
            "Value ({0}) for parameter availabilityZone is invalid. "
            "Subnets can currently only be created in the following availability zones: {1}.".format(
                availability_zone_value, valid_availability_zones
            ),
        )


class AvailabilityZoneNotFromRegionError(EC2ClientError):
    def __init__(self, availability_zone_value):
        super().__init__(
            "InvalidParameterValue",
            "Invalid Availability Zone ({0})".format(availability_zone_value),
        )


class NetworkAclEntryAlreadyExistsError(EC2ClientError):
    def __init__(self, rule_number):
        super().__init__(
            "NetworkAclEntryAlreadyExists",
            "The network acl entry identified by {} already exists.".format(
                rule_number
            ),
        )


class InvalidSubnetRangeError(EC2ClientError):
    def __init__(self, cidr_block):
        super().__init__(
            "InvalidSubnet.Range", "The CIDR '{}' is invalid.".format(cidr_block)
        )


class InvalidCIDRBlockParameterError(EC2ClientError):
    def __init__(self, cidr_block):
        super().__init__(
            "InvalidParameterValue",
            "Value ({}) for parameter cidrBlock is invalid. This is not a valid CIDR block.".format(
                cidr_block
            ),
        )


class InvalidDestinationCIDRBlockParameterError(EC2ClientError):
    def __init__(self, cidr_block):
        super().__init__(
            "InvalidParameterValue",
            "Value ({}) for parameter destinationCidrBlock is invalid. This is not a valid CIDR block.".format(
                cidr_block
            ),
        )


class InvalidSubnetConflictError(EC2ClientError):
    def __init__(self, cidr_block):
        super().__init__(
            "InvalidSubnet.Conflict",
            "The CIDR '{}' conflicts with another subnet".format(cidr_block),
        )


class InvalidVPCRangeError(EC2ClientError):
    def __init__(self, cidr_block):
        super().__init__(
            "InvalidVpc.Range", "The CIDR '{}' is invalid.".format(cidr_block)
        )


# accept exception
class OperationNotPermitted2(EC2ClientError):
    def __init__(self, client_region, pcx_id, acceptor_region):
        super().__init__(
            "OperationNotPermitted",
            "Incorrect region ({0}) specified for this request."
            "VPC peering connection {1} must be accepted in region {2}".format(
                client_region, pcx_id, acceptor_region
            ),
        )


# reject exception
class OperationNotPermitted3(EC2ClientError):
    def __init__(self, client_region, pcx_id, acceptor_region):
        super().__init__(
            "OperationNotPermitted",
            "Incorrect region ({0}) specified for this request."
            "VPC peering connection {1} must be accepted or rejected in region {2}".format(
                client_region, pcx_id, acceptor_region
            ),
        )


class OperationNotPermitted4(EC2ClientError):
    def __init__(self, instance_id):
        super().__init__(
            "OperationNotPermitted",
            "The instance '{0}' may not be terminated. Modify its 'disableApiTermination' "
            "instance attribute and try again.".format(instance_id),
        )


class InvalidLaunchTemplateNameAlreadyExistsError(EC2ClientError):
    def __init__(self):
        super().__init__(
            "InvalidLaunchTemplateName.AlreadyExistsException",
            "Launch template name already in use.",
        )


class InvalidLaunchTemplateNameNotFoundError(EC2ClientError):
    def __init__(self):
        super().__init__(
            "InvalidLaunchTemplateName.NotFoundException",
            "At least one of the launch templates specified in the request does not exist.",
        )


class InvalidParameterDependency(EC2ClientError):
    def __init__(self, param, param_needed):
        super().__init__(
            "InvalidParameterDependency",
            "The parameter [{0}] requires the parameter {1} to be set.".format(
                param, param_needed
            ),
        )


class IncorrectStateIamProfileAssociationError(EC2ClientError):
    def __init__(self, instance_id):
        super().__init__(
            "IncorrectState",
            "There is an existing association for instance {0}".format(instance_id),
        )


class InvalidAssociationIDIamProfileAssociationError(EC2ClientError):
    def __init__(self, association_id):
        super().__init__(
            "InvalidAssociationID.NotFound",
            "An invalid association-id of '{0}' was given".format(association_id),
        )


class InvalidVpcEndPointIdError(EC2ClientError):
    def __init__(self, vpc_end_point_id):
        super().__init__(
            "InvalidVpcEndpointId.NotFound",
            "The VpcEndPoint ID '{0}' does not exist".format(vpc_end_point_id),
        )


class InvalidTaggableResourceType(EC2ClientError):
    def __init__(self, resource_type):
        super().__init__(
            "InvalidParameterValue",
            "'{}' is not a valid taggable resource type for this operation.".format(
                resource_type
            ),
        )


class GenericInvalidParameterValueError(EC2ClientError):
    def __init__(self, attribute, value):
        super().__init__(
            "InvalidParameterValue",
            "invalid value for parameter {0}: {1}".format(attribute, value),
        )


class InvalidSubnetCidrBlockAssociationID(EC2ClientError):
    def __init__(self, association_id):
        super().__init__(
            "InvalidSubnetCidrBlockAssociationID.NotFound",
            "The subnet CIDR block with association ID '{0}' does not exist".format(
                association_id
            ),
        )


class InvalidCarrierGatewayID(EC2ClientError):
    def __init__(self, carrier_gateway_id):
        super().__init__(
            "InvalidCarrierGatewayID.NotFound",
            "The CarrierGateway ID '{0}' does not exist".format(carrier_gateway_id),
        )


class NoLoadBalancersProvided(EC2ClientError):
    def __init__(self):
        super().__init__(
            "InvalidParameter",
            "exactly one of network_load_balancer_arn or gateway_load_balancer_arn is a required member",
        )


class UnknownVpcEndpointService(EC2ClientError):
    def __init__(self, service_id):
        super().__init__(
            "InvalidVpcEndpointServiceId.NotFound",
            f"The VpcEndpointService Id '{service_id}' does not exist",
        )
