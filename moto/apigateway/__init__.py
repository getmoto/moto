from __future__ import unicode_literals
from .models import apigateway_backends
from ..core.models import MockAWS

apigateway_backend = apigateway_backends['us-east-1']


def mock_apigateway(func=None):
    if func:
        return MockAWS(apigateway_backends)(func)
    else:
        return MockAWS(apigateway_backends)
