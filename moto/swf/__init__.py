from __future__ import unicode_literals
from .models import swf_backends
from ..core.models import MockAWS

swf_backend = swf_backends['us-east-1']


def mock_swf(func=None):
    if func:
        return MockAWS(swf_backends)(func)
    else:
        return MockAWS(swf_backends)
