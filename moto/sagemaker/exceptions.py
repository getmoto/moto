from __future__ import unicode_literals
import json
from moto.core.exceptions import RESTError


ERROR_WITH_MODEL_NAME = """{% extends 'single_error' %}
{% block extra %}<ModelName>{{ model }}</ModelName>{% endblock %}
"""


class SagemakerClientError(RESTError):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("template", "single_error")
        self.templates["model_error"] = ERROR_WITH_MODEL_NAME
        super(SagemakerClientError, self).__init__(*args, **kwargs)


class ModelError(RESTError):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("template", "model_error")
        self.templates["model_error"] = ERROR_WITH_MODEL_NAME
        super(ModelError, self).__init__(*args, **kwargs)


class MissingModel(ModelError):
    code = 404

    def __init__(self, *args, **kwargs):
        super(MissingModel, self).__init__(
            "NoSuchModel", "Could not find model", *args, **kwargs
        )


class AWSError(Exception):
    TYPE = None
    STATUS = 400

    def __init__(self, message, type=None, status=None):
        self.message = message
        self.type = type if type is not None else self.TYPE
        self.status = status if status is not None else self.STATUS

    def response(self):
        return (
            json.dumps({"__type": self.type, "message": self.message}),
            dict(status=self.status),
        )
