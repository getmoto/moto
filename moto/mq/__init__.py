"""mq module initialization; sets value for base decorator."""
from .models import mq_backends
from ..core.models import base_decorator

mock_mq = base_decorator(mq_backends)
