from moto.core.exceptions import RESTError


class MessageRejectedError(RESTError):
    code = 400

    def __init__(self, message):
        super().__init__("MessageRejected", message)


class ConfigurationSetDoesNotExist(RESTError):
    code = 400

    def __init__(self, message):
        super().__init__("ConfigurationSetDoesNotExist", message)


class ConfigurationSetAlreadyExists(RESTError):
    code = 400

    def __init__(self, message):
        super().__init__("ConfigurationSetAlreadyExists", message)


class EventDestinationAlreadyExists(RESTError):
    code = 400

    def __init__(self, message):
        super().__init__("EventDestinationAlreadyExists", message)


class TemplateNameAlreadyExists(RESTError):
    code = 400

    def __init__(self, message):
        super().__init__("TemplateNameAlreadyExists", message)


class ValidationError(RESTError):
    code = 400

    def __init__(self, message):
        super().__init__("ValidationError", message)


class InvalidParameterValue(RESTError):
    code = 400

    def __init__(self, message):
        super().__init__("InvalidParameterValue", message)


class InvalidRenderingParameterException:
    code = 400

    def __init__(self, message):
        super().__init__("InvalidRenderingParameterException", message)


class TemplateDoesNotExist(RESTError):
    code = 400

    def __init__(self, message):
        super().__init__("TemplateDoesNotExist", message)


class RuleSetNameAlreadyExists(RESTError):
    code = 400

    def __init__(self, message):
        super().__init__("RuleSetNameAlreadyExists", message)


class RuleAlreadyExists(RESTError):
    code = 400

    def __init__(self, message):
        super().__init__("RuleAlreadyExists", message)


class RuleSetDoesNotExist(RESTError):
    code = 400

    def __init__(self, message):
        super().__init__("RuleSetDoesNotExist", message)


class RuleDoesNotExist(RESTError):
    code = 400

    def __init__(self, message):
        super().__init__("RuleDoesNotExist", message)


class MissingRenderingAttributeException(RESTError):
    code = 400

    def __init__(self, var):
        super().__init__(
            "MissingRenderingAttributeException",
            f"Attribute '{var}' is not present in the rendering data.",
        )
