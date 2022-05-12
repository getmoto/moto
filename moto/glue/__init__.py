from .models import glue_backend
from ..core.models import base_decorator

glue_backends = {"global": glue_backend}
mock_glue = base_decorator(glue_backends)
