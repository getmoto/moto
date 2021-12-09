from .models import elasticache_backends
from ..core.models import base_decorator

mock_elasticache = base_decorator(elasticache_backends)
