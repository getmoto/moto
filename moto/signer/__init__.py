"""signer module initialization; sets value for base decorator."""
from .models import signer_backends
from ..core.models import base_decorator

mock_signer = base_decorator(signer_backends)
