from .models import kinesis_backends
from ..core.models import base_decorator, deprecated_base_decorator

kinesis_backend = kinesis_backends["us-east-1"]
mock_kinesis = base_decorator(kinesis_backends)
mock_kinesis_deprecated = deprecated_base_decorator(kinesis_backends)
