from __future__ import unicode_literals
from .models import emr_backends
from ..core.models import MockAWS

emr_backend = emr_backends['us-east-1']


def mock_emr(func=None):
    if func:
        return MockAWS(emr_backends)(func)
    else:
        return MockAWS(emr_backends)
