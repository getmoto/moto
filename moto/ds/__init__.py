"""ds module initialization; sets value for base decorator."""
from ..core.models import base_decorator
from .models import ds_backends

mock_ds = base_decorator(ds_backends)
