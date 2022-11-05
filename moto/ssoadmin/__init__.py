"""ssoadmin module initialization; sets value for base decorator."""
from .models import ssoadmin_backends
from ..core.models import base_decorator

mock_ssoadmin = base_decorator(ssoadmin_backends)
