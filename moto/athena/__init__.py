from .models import athena_backends
from ..core.models import base_decorator, deprecated_base_decorator

athena_backend = athena_backends["us-east-1"]
mock_athena = base_decorator(athena_backends)
mock_athena_deprecated = deprecated_base_decorator(athena_backends)
