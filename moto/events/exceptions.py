from __future__ import unicode_literals
from moto.core.exceptions import JsonRESTError


class ValidationException(JsonRESTError):
    code = 400

    def __init__(self, message):
        super(ValidationException, self).__init__("ValidationException", message)
