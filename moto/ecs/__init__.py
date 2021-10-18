from .models import ecs_backends
from ..core.models import base_decorator

ecs_backend = ecs_backends["us-east-1"]
mock_ecs = base_decorator(ecs_backends)
