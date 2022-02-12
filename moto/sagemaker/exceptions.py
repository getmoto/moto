from moto.core.exceptions import RESTError, JsonRESTError, AWSError

ERROR_WITH_MODEL_NAME = """{% extends 'single_error' %}
{% block extra %}<ModelName>{{ model }}</ModelName>{% endblock %}
"""


class SagemakerClientError(RESTError):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("template", "single_error")
        self.templates["model_error"] = ERROR_WITH_MODEL_NAME
        super().__init__(*args, **kwargs)


class ModelError(RESTError):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("template", "model_error")
        self.templates["model_error"] = ERROR_WITH_MODEL_NAME
        super().__init__(*args, **kwargs)


class MissingModel(ModelError):
    code = 404

    def __init__(self, *args, **kwargs):
        super().__init__("NoSuchModel", "Could not find model", *args, **kwargs)


class ValidationError(JsonRESTError):
    def __init__(self, message, **kwargs):
        super().__init__("ValidationException", message, **kwargs)


class AWSValidationException(AWSError):
    TYPE = "ValidationException"


class ResourceNotFound(JsonRESTError):
    def __init__(self, message, **kwargs):
        super().__init__(__class__.__name__, message, **kwargs)
