from ..core.models import base_decorator
from .models import elasticache_backends

mock_elasticache = base_decorator(elasticache_backends)
