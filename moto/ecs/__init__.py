from __future__ import unicode_literals
from .models import ecs_backends
from ..core.models import MockAWS, base_decorator, HttprettyMockAWS, deprecated_base_decorator

ecs_backend = ecs_backends['us-east-1']
mock_ecs = base_decorator(ecs_backends)
mock_ecs_deprecated = deprecated_base_decorator(ecs_backends)
