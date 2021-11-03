from .models import support_backends
from ..core.models import base_decorator

support_backend = support_backends["us-east-1"]
mock_support = base_decorator(support_backends)
