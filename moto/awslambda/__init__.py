from __future__ import unicode_literals
from .models import lambda_backends
from ..core.models import MockAWS


lambda_backend = lambda_backends['us-east-1']


def mock_lambda(func=None):
    if func:
        return MockAWS(lambda_backends)(func)
    else:
        return MockAWS(lambda_backends)
