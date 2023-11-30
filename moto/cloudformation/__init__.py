from ..core.models import base_decorator
from .models import cloudformation_backends

cloudformation_backend = cloudformation_backends["us-east-1"]
mock_cloudformation = base_decorator(cloudformation_backends)
