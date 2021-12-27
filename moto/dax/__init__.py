"""dax module initialization; sets value for base decorator."""
from .models import dax_backends
from ..core.models import base_decorator

mock_dax = base_decorator(dax_backends)
