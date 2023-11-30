from ..core.models import base_decorator
from .models import ssm_backends

mock_ssm = base_decorator(ssm_backends)
