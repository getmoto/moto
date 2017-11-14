from __future__ import unicode_literals
from .models import iotdata_backends
from ..core.models import base_decorator

iotdata_backend = iotdata_backends['us-east-1']
mock_iotdata = base_decorator(iotdata_backends)
