from ..core.models import base_decorator
from .models import ecr_backends

ecr_backend = ecr_backends["us-east-1"]
mock_ecr = base_decorator(ecr_backends)
