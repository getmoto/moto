from typing import Any
from moto.core.exceptions import RESTError, JsonRESTError, AWSError

ERROR_WITH_MODEL_NAME = """{% extends 'single_error' %}
{% block extra %}<ModelName>{{ model }}</ModelName>{% endblock %}
"""


class SagemakerClientError(RESTError):
    def __init__(self, *args: Any, **kwargs: Any):
        kwargs.setdefault("template", "single_error")
        self.templates["model_error"] = ERROR_WITH_MODEL_NAME
        super().__init__(*args, **kwargs)


class ModelError(RESTError):
    def __init__(self, *args: Any, **kwargs: Any):
        kwargs.setdefault("template", "model_error")
        self.templates["model_error"] = ERROR_WITH_MODEL_NAME
        super().__init__(*args, **kwargs)


class MissingModel(ModelError):
    code = 404

    def __init__(self, model: str):
        super().__init__("NoSuchModel", "Could not find model", model=model)


class ValidationError(JsonRESTError):
    def __init__(self, message: str):
        super().__init__("ValidationException", message)


class AWSValidationException(AWSError):
    TYPE = "ValidationException"


class ResourceNotFound(JsonRESTError):
    def __init__(self, message: str):
        super().__init__(__class__.__name__, message)  # type: ignore
