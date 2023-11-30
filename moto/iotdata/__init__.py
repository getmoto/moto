from ..core.models import base_decorator
from .models import iotdata_backends

mock_iotdata = base_decorator(iotdata_backends)
