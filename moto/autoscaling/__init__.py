from __future__ import unicode_literals
from .models import autoscaling_backend, autoscaling_backends  # flake8: noqa
from ..core.models import MockAWS


def mock_autoscaling(func=None):
    if func:
        return MockAWS(autoscaling_backends)(func)
    else:
        return MockAWS(autoscaling_backends)
