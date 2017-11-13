from __future__ import unicode_literals
from moto.core.exceptions import RESTError


class SNSNotFoundError(RESTError):
    code = 404

    def __init__(self, message):
        super(SNSNotFoundError, self).__init__(
            "NotFound", message)


class DuplicateSnsEndpointError(RESTError):
    code = 400

    def __init__(self, message):
        super(DuplicateSnsEndpointError, self).__init__(
            "DuplicateEndpoint", message)


class SnsEndpointDisabled(RESTError):
    code = 400

    def __init__(self, message):
        super(SnsEndpointDisabled, self).__init__(
            "EndpointDisabled", message)


class SNSInvalidParameter(RESTError):
    code = 400

    def __init__(self, message):
        super(SNSInvalidParameter, self).__init__(
            "InvalidParameter", message)


class InvalidParameterValue(RESTError):
    code = 400

    def __init__(self, message):
        super(InvalidParameterValue, self).__init__(
            "InvalidParameterValue", message)
