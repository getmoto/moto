from .models import sts_backend
from ..core.models import base_decorator

sts_backends = {"global": sts_backend}
mock_sts = base_decorator(sts_backends)
