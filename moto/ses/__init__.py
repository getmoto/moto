from ..core.models import base_decorator
from .models import ses_backends

mock_ses = base_decorator(ses_backends)
