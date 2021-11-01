"""ds module initialization; sets value for base decorator."""
from .models import ds_backends
from ..core.models import base_decorator

mock_ds = base_decorator(ds_backends)
