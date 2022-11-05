from .models import glue_backends
from ..core.models import base_decorator

mock_glue = base_decorator(glue_backends)
