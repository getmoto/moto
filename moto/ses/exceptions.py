from moto.core.exceptions import ServiceException


class SesError(ServiceException):
    pass


class MessageRejectedError(SesError):
    def __init__(self, message: str):
        super().__init__("MessageRejected", message)


class ConfigurationSetDoesNotExist(SesError):
    def __init__(self, message: str):
        super().__init__("ConfigurationSetDoesNotExist", message)


class ConfigurationSetAlreadyExists(SesError):
    def __init__(self, message: str):
        super().__init__("ConfigurationSetAlreadyExists", message)


class EventDestinationAlreadyExists(SesError):
    def __init__(self, message: str):
        super().__init__("EventDestinationAlreadyExists", message)


class TemplateNameAlreadyExists(SesError):
    def __init__(self, message: str):
        super().__init__("TemplateNameAlreadyExists", message)


class ValidationError(SesError):
    def __init__(self, message: str):
        super().__init__("ValidationError", message)


class InvalidParameterValue(SesError):
    def __init__(self, message: str):
        super().__init__("InvalidParameterValue", message)


class InvalidRenderingParameterException(SesError):
    def __init__(self, message: str):
        super().__init__("InvalidRenderingParameterException", message)


class TemplateDoesNotExist(SesError):
    def __init__(self, message: str):
        super().__init__("TemplateDoesNotExist", message)


class AlreadyExists(SesError):
    def __init__(self, message: str):
        super().__init__("AlreadyExists", message)


class RuleSetDoesNotExist(SesError):
    def __init__(self, message: str):
        super().__init__("RuleSetDoesNotExist", message)


class RuleDoesNotExist(SesError):
    def __init__(self, message: str):
        super().__init__("RuleDoesNotExist", message)


class MissingRenderingAttributeException(SesError):
    def __init__(self, var: str):
        super().__init__(
            "MissingRenderingAttributeException",
            f"Attribute '{var}' is not present in the rendering data.",
        )
