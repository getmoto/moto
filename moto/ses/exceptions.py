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


class TemplateDoesNotExist(RESTError):
    code = 400

    def __init__(self, message):
        super(TemplateDoesNotExist, self).__init__("TemplateDoesNotExist", message)
