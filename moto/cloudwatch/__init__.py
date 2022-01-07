from .models import cloudwatch_backends
from ..core.models import base_decorator

mock_cloudwatch = base_decorator(cloudwatch_backends)
