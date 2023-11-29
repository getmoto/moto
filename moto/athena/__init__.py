from ..core.models import base_decorator
from .models import athena_backends

athena_backend = athena_backends["us-east-1"]
mock_athena = base_decorator(athena_backends)
