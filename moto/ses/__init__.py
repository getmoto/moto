from .models import ses_backends
from ..core.models import base_decorator

mock_ses = base_decorator(ses_backends)
