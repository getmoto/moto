"""ebs module initialization; sets value for base decorator."""
from .models import ebs_backends
from ..core.models import base_decorator

mock_ebs = base_decorator(ebs_backends)
