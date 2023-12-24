from ..core.models import base_decorator
from .models import glacier_backends

glacier_backend = glacier_backends["us-east-1"]
mock_glacier = base_decorator(glacier_backends)
