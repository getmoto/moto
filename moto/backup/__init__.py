"""backup module initialization; sets value for base decorator."""
from ..core.models import base_decorator
from .models import backup_backends

mock_backup = base_decorator(backup_backends)
