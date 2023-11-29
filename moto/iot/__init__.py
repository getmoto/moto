from ..core.models import base_decorator
from .models import iot_backends

mock_iot = base_decorator(iot_backends)
