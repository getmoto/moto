from ..core.models import base_decorator
from .models import support_backends

mock_support = base_decorator(support_backends)
