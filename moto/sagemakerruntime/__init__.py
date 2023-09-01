"""sagemakerruntime module initialization; sets value for base decorator."""
from .models import sagemakerruntime_backends
from ..core.models import base_decorator

mock_sagemakerruntime = base_decorator(sagemakerruntime_backends)
