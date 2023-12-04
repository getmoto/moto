from ..core.models import base_decorator
from .models import cognitoidp_backends

mock_cognitoidp = base_decorator(cognitoidp_backends)
