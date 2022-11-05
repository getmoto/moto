from .models import batch_backends
from ..core.models import base_decorator

batch_backend = batch_backends["us-east-1"]
mock_batch = base_decorator(batch_backends)
