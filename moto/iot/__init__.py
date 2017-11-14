from __future__ import unicode_literals
from .models import iot_backends
from ..core.models import base_decorator

iot_backend = iot_backends['us-east-1']
mock_iot = base_decorator(iot_backends)
