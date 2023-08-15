"""apigatewaymanagementapi module initialization; sets value for base decorator."""
from .models import apigatewaymanagementapi_backends
from ..core.models import base_decorator

mock_apigatewaymanagementapi = base_decorator(apigatewaymanagementapi_backends)
