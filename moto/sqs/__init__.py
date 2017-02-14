from __future__ import unicode_literals
from .models import sqs_backends
from ..core.models import MockAWS, base_decorator

sqs_backend = sqs_backends['us-east-1']
mock_sqs = base_decorator(sqs_backends)
