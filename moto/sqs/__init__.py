from __future__ import unicode_literals
from .models import sqs_backends, sqs_backend  # flake8: noqa
from ..core.models import MockAWS


def mock_sqs(func=None):
    if func:
        return MockAWS(sqs_backends)(func)
    else:
        return MockAWS(sqs_backends)
