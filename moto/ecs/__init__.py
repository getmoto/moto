from __future__ import unicode_literals
from .models import ecs_backends
from ..core.models import base_decorator, deprecated_base_decorator, atidot_base_decorator
bk = ecs_backends
ecs_backend = bk["us-east-1"]
mock_ecs = atidot_base_decorator(bk)
mock_ecs_deprecated = deprecated_base_decorator(bk)
