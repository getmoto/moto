"""ssoadmin module initialization; sets value for base decorator."""
from ..core.models import base_decorator
from .models import ssoadmin_backends

mock_ssoadmin = base_decorator(ssoadmin_backends)
