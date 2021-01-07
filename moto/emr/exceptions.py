from __future__ import unicode_literals

from moto.core.exceptions import RESTError, JsonRESTError


class EmrError(RESTError):
    code = 400


class InvalidRequestException(JsonRESTError):
    def __init__(self, message, **kwargs):
        super(InvalidRequestException, self).__init__(
            "InvalidRequestException", message, **kwargs
        )
