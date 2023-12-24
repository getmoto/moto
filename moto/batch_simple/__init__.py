from ..core.models import base_decorator
from .models import batch_simple_backends

batch_backend = batch_simple_backends["us-east-1"]
mock_batch_simple = base_decorator(batch_simple_backends)
