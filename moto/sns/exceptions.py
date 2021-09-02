from __future__ import unicode_literals
from moto.core.exceptions import RESTError


class SNSNotFoundError(RESTError):
    code = 404

    def __init__(self, message, **kwargs):
        super().__init__("NotFound", message, **kwargs)


class ResourceNotFoundError(RESTError):
    code = 404

    def __init__(self):
        super(ResourceNotFoundError, self).__init__(
            "ResourceNotFound", "Resource does not exist"
        )


class DuplicateSnsEndpointError(RESTError):
    code = 400

    def __init__(self, message):
        super(DuplicateSnsEndpointError, self).__init__("DuplicateEndpoint", message)


class SnsEndpointDisabled(RESTError):
    code = 400

    def __init__(self, message):
        super(SnsEndpointDisabled, self).__init__("EndpointDisabled", message)


class SNSInvalidParameter(RESTError):
    code = 400

    def __init__(self, message):
        super(SNSInvalidParameter, self).__init__("InvalidParameter", message)


class InvalidParameterValue(RESTError):
    code = 400

    def __init__(self, message):
        super(InvalidParameterValue, self).__init__("InvalidParameterValue", message)


class TagLimitExceededError(RESTError):
    code = 400

    def __init__(self):
        super(TagLimitExceededError, self).__init__(
            "TagLimitExceeded",
            "Could not complete request: tag quota of per resource exceeded",
        )


class InternalError(RESTError):
    code = 500

    def __init__(self, message):
        super(InternalError, self).__init__("InternalFailure", message)
