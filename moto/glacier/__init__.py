from __future__ import unicode_literals
from .models import glacier_backends
from ..core.models import MockAWS

glacier_backend = glacier_backends['us-east-1']


def mock_glacier(func=None):
    if func:
        return MockAWS(glacier_backends)(func)
    else:
        return MockAWS(glacier_backends)
