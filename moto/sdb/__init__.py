"""sdb module initialization; sets value for base decorator."""
from ..core.models import base_decorator
from .models import sdb_backends

mock_sdb = base_decorator(sdb_backends)
