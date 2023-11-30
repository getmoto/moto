"""apigatewayv2 module initialization; sets value for base decorator."""
from ..core.models import base_decorator
from .models import apigatewayv2_backends

mock_apigatewayv2 = base_decorator(apigatewayv2_backends)
