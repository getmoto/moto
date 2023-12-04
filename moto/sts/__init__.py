from ..core.models import base_decorator
from .models import sts_backends

mock_sts = base_decorator(sts_backends)
