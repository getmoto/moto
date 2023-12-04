from ..core.models import base_decorator
from .models import cloudwatch_backends

mock_cloudwatch = base_decorator(cloudwatch_backends)
