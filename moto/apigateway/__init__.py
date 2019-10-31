from __future__ import unicode_literals
from .models import apigateway_backends
from ..core.models import base_decorator, deprecated_base_decorator

apigateway_backend = apigateway_backends["us-east-1"]
mock_apigateway = base_decorator(apigateway_backends)
mock_apigateway_deprecated = deprecated_base_decorator(apigateway_backends)
