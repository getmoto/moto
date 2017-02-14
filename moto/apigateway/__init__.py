from __future__ import unicode_literals
from .models import apigateway_backends
from ..core.models import MockAWS, base_decorator

apigateway_backend = apigateway_backends['us-east-1']
mock_apigateway = base_decorator(apigateway_backends)
