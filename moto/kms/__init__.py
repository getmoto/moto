from __future__ import unicode_literals
from .models import kms_backends
from ..core.models import MockAWS

kms_backend = kms_backends['us-east-1']


def mock_kms(func=None):
    if func:
        return MockAWS(kms_backends)(func)
    else:
        return MockAWS(kms_backends)
