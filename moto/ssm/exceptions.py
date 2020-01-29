from __future__ import unicode_literals
from moto.core.exceptions import JsonRESTError


class InvalidFilterKey(JsonRESTError):
    code = 400

    def __init__(self, message):
        super(InvalidFilterKey, self).__init__("InvalidFilterKey", message)


class InvalidFilterOption(JsonRESTError):
    code = 400

    def __init__(self, message):
        super(InvalidFilterOption, self).__init__("InvalidFilterOption", message)


class InvalidFilterValue(JsonRESTError):
    code = 400

    def __init__(self, message):
        super(InvalidFilterValue, self).__init__("InvalidFilterValue", message)


class ValidationException(JsonRESTError):
    code = 400

    def __init__(self, message):
        super(ValidationException, self).__init__("ValidationException", message)
