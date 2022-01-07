from .models import iot_backends
from ..core.models import base_decorator

mock_iot = base_decorator(iot_backends)
