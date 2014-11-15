from __future__ import unicode_literals
from .models import autoscaling_backends
from ..core.models import MockAWS

autoscaling_backend = autoscaling_backends['us-east-1']


def mock_autoscaling(func=None):
    if func:
        return MockAWS(autoscaling_backends)(func)
    else:
        return MockAWS(autoscaling_backends)
