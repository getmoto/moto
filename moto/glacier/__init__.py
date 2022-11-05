from .models import glacier_backends
from ..core.models import base_decorator

glacier_backend = glacier_backends["us-east-1"]
mock_glacier = base_decorator(glacier_backends)
