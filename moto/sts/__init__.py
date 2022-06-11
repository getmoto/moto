from .models import sts_backends
from ..core.models import base_decorator

mock_sts = base_decorator(sts_backends)
