from .models import iotdata_backends
from ..core.models import base_decorator

mock_iotdata = base_decorator(iotdata_backends)
