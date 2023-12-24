"""ebs module initialization; sets value for base decorator."""
from ..core.models import base_decorator
from .models import ebs_backends

mock_ebs = base_decorator(ebs_backends)
