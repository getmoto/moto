from __future__ import unicode_literals
from .models import kinesis_backends
from ..core.models import MockAWS

kinesis_backend = kinesis_backends['us-east-1']


def mock_kinesis(func=None):
    if func:
        return MockAWS(kinesis_backends)(func)
    else:
        return MockAWS(kinesis_backends)
