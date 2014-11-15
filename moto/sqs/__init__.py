from __future__ import unicode_literals
from .models import sqs_backends
from ..core.models import MockAWS

sqs_backend = sqs_backends['us-east-1']


def mock_sqs(func=None):
    if func:
        return MockAWS(sqs_backends)(func)
    else:
        return MockAWS(sqs_backends)
