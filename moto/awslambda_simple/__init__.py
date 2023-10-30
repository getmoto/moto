from .models import lambda_simple_backends
from ..core.models import base_decorator

lambda_simple_backend = lambda_simple_backends["us-east-1"]
mock_lambda_simple = base_decorator(lambda_simple_backends)
