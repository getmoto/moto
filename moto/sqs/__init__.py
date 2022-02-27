from .models import sqs_backends
from ..core.models import base_decorator

sqs_backend = sqs_backends["us-east-1"]
mock_sqs = base_decorator(sqs_backends)
