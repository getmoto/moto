from ..core.models import base_decorator
from .models import glue_backends

mock_glue = base_decorator(glue_backends)
