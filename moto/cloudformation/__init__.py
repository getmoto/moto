from __future__ import unicode_literals
from .models import cloudformation_backends, cloudformation_backend  # flake8: noqa
from ..core.models import MockAWS


def mock_cloudformation(func=None):
    if func:
        return MockAWS(cloudformation_backends)(func)
    else:
        return MockAWS(cloudformation_backends)
