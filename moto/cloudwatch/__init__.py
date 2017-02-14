from .models import cloudwatch_backends
from ..core.models import MockAWS, base_decorator

cloudwatch_backend = cloudwatch_backends['us-east-1']
mock_cloudwatch = base_decorator(cloudwatch_backends)
