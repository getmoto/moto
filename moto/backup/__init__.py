"""backup module initialization; sets value for base decorator."""
from .models import backup_backends
from ..core.models import base_decorator

mock_backup = base_decorator(backup_backends)