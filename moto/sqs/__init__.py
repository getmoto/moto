from ..core.models import base_decorator
from .models import sqs_backends

mock_sqs = base_decorator(sqs_backends)
