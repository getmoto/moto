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


class InvalidParameterValueError(EC2ClientError):
    def __init__(self, parameter_value):
            super(InvalidParameterValueError, self).__init__(
                "InvalidParameterValue",
                "Value ({0}) for parameter value is invalid. Invalid DHCP option value.".format(
                    parameter_value))




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
