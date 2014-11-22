from __future__ import unicode_literals
from .models import redshift_backends
from ..core.models import MockAWS

redshift_backend = redshift_backends['us-east-1']


def mock_redshift(func=None):
    if func:
        return MockAWS(redshift_backends)(func)
    else:
        return MockAWS(redshift_backends)
