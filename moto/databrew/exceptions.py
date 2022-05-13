from moto.core.exceptions import JsonRESTError


class DataBrewClientError(JsonRESTError):
    code = 400


class AlreadyExistsException(DataBrewClientError):
    def __init__(self, typ):
        super().__init__("AlreadyExistsException", "%s already exists." % (typ))


class ConflictException(DataBrewClientError):
    code = 409

    def __init__(self, message, **kwargs):
        super().__init__("ConflictException", message, **kwargs)


class ValidationException(DataBrewClientError):
    def __init__(self, message, **kwargs):
        super().__init__("ValidationException", message, **kwargs)


class RulesetAlreadyExistsException(AlreadyExistsException):
    def __init__(self):
        super().__init__("Ruleset")


class EntityNotFoundException(DataBrewClientError):
    def __init__(self, msg):
        super().__init__("EntityNotFoundException", msg)


class ResourceNotFoundException(DataBrewClientError):
    code = 404

    def __init__(self, message, **kwargs):
        super().__init__("ResourceNotFoundException", message, **kwargs)


class RulesetNotFoundException(EntityNotFoundException):
    def __init__(self, recipe_name):
        super().__init__("Ruleset %s not found." % recipe_name)


class ServiceQuotaExceededException(JsonRESTError):
    code = 402

    def __init__(self):
        super().__init__(
            "ServiceQuotaExceededException", "A service quota is exceeded."
        )
