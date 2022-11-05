"""appsync module initialization; sets value for base decorator."""
from .models import appsync_backends
from ..core.models import base_decorator

mock_appsync = base_decorator(appsync_backends)
