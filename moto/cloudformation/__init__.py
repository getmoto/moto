from __future__ import unicode_literals
from .models import cloudformation_backends
from ..core.models import MockAWS

cloudformation_backend = cloudformation_backends['us-east-1']


def mock_cloudformation(func=None):
    if func:
        return MockAWS(cloudformation_backends)(func)
    else:
        return MockAWS(cloudformation_backends)
