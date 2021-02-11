from __future__ import unicode_literals
from moto.core.exceptions import RESTError


class MessageRejectedError(RESTError):
    code = 400

    def __init__(self, message):
        super(MessageRejectedError, self).__init__("MessageRejected", message)


class ConfigurationSetDoesNotExist(RESTError):
    code = 400

    def __init__(self, message):
        super(ConfigurationSetDoesNotExist, self).__init__(
            "ConfigurationSetDoesNotExist", message
        )


class EventDestinationAlreadyExists(RESTError):
    code = 400

    def __init__(self, message):
        super(EventDestinationAlreadyExists, self).__init__(
            "EventDestinationAlreadyExists", message
        )


class TemplateNameAlreadyExists(RESTError):
    code = 400

    def __init__(self, message):
        super(TemplateNameAlreadyExists, self).__init__(
            "TemplateNameAlreadyExists", message
        )


class ValidationError(RESTError):
    code = 400

    def __init__(self, message):
        super(ValidationError, self).__init__("ValidationError", message)


class InvalidParameterValue(RESTError):
    code = 400

    def __init__(self, message):
        super(InvalidParameterValue, self).__init__("InvalidParameterValue", message)


class InvalidRenderingParameterException:
    code = 400

    def __init__(self, message):
        super(InvalidRenderingParameterException, self).__init__(
            "InvalidRenderingParameterException", message
        )


class TemplateDoesNotExist(RESTError):
    code = 400

    def __init__(self, message):
        super(TemplateDoesNotExist, self).__init__("TemplateDoesNotExist", message)


class RuleSetNameAlreadyExists(RESTError):
    code = 400

    def __init__(self, message):
        super(RuleSetNameAlreadyExists, self).__init__(
            "RuleSetNameAlreadyExists", message
        )


class RuleAlreadyExists(RESTError):
    code = 400

    def __init__(self, message):
        super(RuleAlreadyExists, self).__init__("RuleAlreadyExists", message)


class RuleSetDoesNotExist(RESTError):
    code = 400

    def __init__(self, message):
        super(RuleSetDoesNotExist, self).__init__("RuleSetDoesNotExist", message)
