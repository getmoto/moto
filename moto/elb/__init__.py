from __future__ import unicode_literals
from .models import elb_backends, elb_backend  # flake8: noqa
from ..core.models import MockAWS


def mock_elb(func=None):
    if func:
        return MockAWS(elb_backends)(func)
    else:
        return MockAWS(elb_backends)
