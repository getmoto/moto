from .models import sqs_backends
from ..core.models import base_decorator

mock_sqs = base_decorator(sqs_backends)
