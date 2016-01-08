from __future__ import unicode_literals
from .models import ecs_backends
from ..core.models import MockAWS

ecs_backend = ecs_backends['us-east-1']

def mock_ecs(func=None):
    if func:
        return MockAWS(ecs_backends)(func)
    else:
        return MockAWS(ecs_backends)
