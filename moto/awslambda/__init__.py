from ..core.models import base_decorator
from .models import lambda_backends

lambda_backend = lambda_backends["us-east-1"]
mock_lambda = base_decorator(lambda_backends)
