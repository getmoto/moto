from __future__ import unicode_literals
from .models import rds_backends
from ..core.models import MockAWS

rds_backend = rds_backends['us-east-1']


def mock_rds(func=None):
    if func:
        return MockAWS(rds_backends)(func)
    else:
        return MockAWS(rds_backends)
