from __future__ import unicode_literals
from .models import opsworks_backends
from ..core.models import MockAWS

opsworks_backend = opsworks_backends['us-east-1']


def mock_opsworks(func=None):
    if func:
        return MockAWS(opsworks_backends)(func)
    else:
        return MockAWS(opsworks_backends)

