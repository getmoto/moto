from __future__ import unicode_literals
from moto.core.exceptions import JsonRESTError


class InvalidParameterException(JsonRESTError):
    code = 400

    def __init__(self, message):
        super(InvalidParameterException, self).__init__(
            "InvalidParameterException", message
        )


class MalformedArnException(JsonRESTError):
    code = 400

    def __init__(self, message):
        super(MalformedArnException, self).__init__("MalformedArnException", message)


class UnknownResourceException(JsonRESTError):
    code = 400

    def __init__(self, message):
        super(UnknownResourceException, self).__init__(
            "UnknownResourceException", message
        )
