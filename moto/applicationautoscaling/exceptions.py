from __future__ import unicode_literals
from moto.core.exceptions import JsonRESTError


class AWSValidationException(JsonRESTError):
    def __init__(self, message, **kwargs):
        super(AWSValidationException, self).__init__(
            "ValidationException", message, **kwargs
        )
