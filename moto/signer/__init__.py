"""signer module initialization; sets value for base decorator."""
from ..core.models import base_decorator
from .models import signer_backends

mock_signer = base_decorator(signer_backends)
