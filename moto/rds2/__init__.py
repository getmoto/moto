from __future__ import unicode_literals
from .models import rds2_backends
from ..core.models import MockAWS

rds2_backend = rds2_backends['us-west-1']


def mock_rds2(func=None):
    if func:
        return MockAWS(rds2_backends)(func)
    else:
        return MockAWS(rds2_backends)
