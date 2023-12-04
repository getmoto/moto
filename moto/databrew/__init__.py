from ..core.models import base_decorator
from .models import databrew_backends

mock_databrew = base_decorator(databrew_backends)
