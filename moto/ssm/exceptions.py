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


class ParameterNotFound(JsonRESTError):
    code = 400

    def __init__(self, message):
        super(ParameterNotFound, self).__init__("ParameterNotFound", message)


class ParameterVersionNotFound(JsonRESTError):
    code = 400

    def __init__(self, message):
        super(ParameterVersionNotFound, self).__init__(
            "ParameterVersionNotFound", message
        )


class ParameterVersionLabelLimitExceeded(JsonRESTError):
    code = 400

    def __init__(self, message):
        super(ParameterVersionLabelLimitExceeded, self).__init__(
            "ParameterVersionLabelLimitExceeded", message
        )


class ValidationException(JsonRESTError):
    code = 400

    def __init__(self, message):
        super(ValidationException, self).__init__("ValidationException", message)
