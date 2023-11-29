"""mq module initialization; sets value for base decorator."""
from ..core.models import base_decorator
from .models import mq_backends

mock_mq = base_decorator(mq_backends)
