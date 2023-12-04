from ..core.models import base_decorator
from .models import batch_backends

batch_backend = batch_backends["us-east-1"]
mock_batch = base_decorator(batch_backends)
