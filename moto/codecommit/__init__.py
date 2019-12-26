from .models import codecommit_backends
from ..core.models import base_decorator

mock_codecommit = base_decorator(codecommit_backends)
