from .models import ssm_backends
from ..core.models import base_decorator

mock_ssm = base_decorator(ssm_backends)
