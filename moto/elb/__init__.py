from __future__ import unicode_literals
from .models import elb_backends
from ..core.models import MockAWS

elb_backend = elb_backends['us-east-1']


def mock_elb(func=None):
    if func:
        return MockAWS(elb_backends)(func)
    else:
        return MockAWS(elb_backends)
