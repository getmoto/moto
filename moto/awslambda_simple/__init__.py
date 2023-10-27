from .models import lambda_simple_backends
from ..core.models import base_decorator

batch_backend = lambda_simple_backends["us-east-1"]
mock_batch_simple = base_decorator(lambda_simple_backends)
