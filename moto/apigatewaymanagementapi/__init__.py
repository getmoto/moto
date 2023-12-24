"""apigatewaymanagementapi module initialization; sets value for base decorator."""
from ..core.models import base_decorator
from .models import apigatewaymanagementapi_backends

mock_apigatewaymanagementapi = base_decorator(apigatewaymanagementapi_backends)
