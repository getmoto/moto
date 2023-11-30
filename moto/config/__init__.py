from ..core.models import base_decorator
from .models import config_backends

mock_config = base_decorator(config_backends)
