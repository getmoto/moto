from __future__ import unicode_literals
from .models import kinesis_backends
from ..core.models import MockAWS, base_decorator

kinesis_backend = kinesis_backends['us-east-1']
mock_kinesis = base_decorator(kinesis_backends)
