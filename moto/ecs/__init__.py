from __future__ import unicode_literals
from .models import ecs_backends
from ..core.models import MockAWS, base_decorator

ecs_backend = ecs_backends['us-east-1']
mock_ecs = base_decorator(ecs_backends)
