"""sdb module initialization; sets value for base decorator."""
from .models import sdb_backends
from ..core.models import base_decorator

mock_sdb = base_decorator(sdb_backends)
