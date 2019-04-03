from .models import config_backends
from ..core.models import base_decorator

mock_config = base_decorator(config_backends)
