from __future__ import unicode_literals
from .models import ec2_backend, ec2_backends  # flake8: noqa
from ..core.models import MockAWS


def mock_ec2(func=None):
    if func:
        return MockAWS(ec2_backends)(func)
    else:
        return MockAWS(ec2_backends)
