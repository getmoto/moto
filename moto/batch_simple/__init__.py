from .models import batch_simple_backends
from ..core.models import base_decorator

batch_backend = batch_simple_backends["us-east-1"]
mock_batch_simple = base_decorator(batch_simple_backends)
