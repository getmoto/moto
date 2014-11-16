from __future__ import unicode_literals
from .models import sns_backends
from ..core.models import MockAWS

sns_backend = sns_backends['us-east-1']


def mock_sns(func=None):
    if func:
        return MockAWS(sns_backends)(func)
    else:
        return MockAWS(sns_backends)
