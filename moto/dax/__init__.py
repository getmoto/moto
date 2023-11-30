"""dax module initialization; sets value for base decorator."""
from ..core.models import base_decorator
from .models import dax_backends

mock_dax = base_decorator(dax_backends)
