from .models import databrew_backends
from ..core.models import base_decorator

mock_databrew = base_decorator(databrew_backends)
