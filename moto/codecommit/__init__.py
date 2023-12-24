from ..core.models import base_decorator
from .models import codecommit_backends

mock_codecommit = base_decorator(codecommit_backends)
