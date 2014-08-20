from werkzeug.exceptions import BadRequest
from jinja2 import Template


class InvalidIdError(RuntimeError):
    def __init__(self, id_value):
        super(InvalidIdError, self).__init__()
        self.id = id_value


class EC2ClientError(BadRequest):
    def __init__(self, code, message):
        super(EC2ClientError, self).__init__()
        self.description = ERROR_RESPONSE_TEMPLATE.render(
            code=code, message=message)


class DependencyViolationError(EC2ClientError):
    def __init__(self, message):
        super(DependencyViolationError, self).__init__(
            "DependencyViolation", message)


class InvalidDHCPOptionsIdError(EC2ClientError):
    def __init__(self, dhcp_options_id):
        super(InvalidDHCPOptionsIdError, self).__init__(
            "InvalidDhcpOptionID.NotFound",
            "DhcpOptionID {0} does not exist."
            .format(dhcp_options_id))


class InvalidVPCIdError(EC2ClientError):
    def __init__(self, vpc_id):
        super(InvalidVPCIdError, self).__init__(
            "InvalidVpcID.NotFound",
            "VpcID {0} does not exist."
            .format(vpc_id))


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


class InvalidInternetGatewayIDError(EC2ClientError):
    def __init__(self, internet_gateway_id):
        super(InvalidInternetGatewayIDError, self).__init__(
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
    def __init__(self, resource):
        super(ResourceAlreadyAssociatedError, self).__init__(
            "Resource.AlreadyAssociated",
            "Resource {0} is already associated."
            .format(str(resource)))


ERROR_RESPONSE = u"""<?xml version="1.0" encoding="UTF-8"?>
  <Response>
    <Errors>
      <Error>
        <Code>{{code}}</Code>
        <Message>{{message}}</Message>
      </Error>
    </Errors>
  <RequestID>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</RequestID>
</Response>
"""
ERROR_RESPONSE_TEMPLATE = Template(ERROR_RESPONSE)
