from .models import support_backends
from ..core.models import base_decorator

mock_support = base_decorator(support_backends)
