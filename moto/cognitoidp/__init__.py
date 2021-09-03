from .models import cognitoidp_backends
from ..core.models import base_decorator, deprecated_base_decorator

mock_cognitoidp = base_decorator(cognitoidp_backends)
mock_cognitoidp_deprecated = deprecated_base_decorator(cognitoidp_backends)
