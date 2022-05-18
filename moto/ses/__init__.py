from .models import ses_backend
from ..core.models import base_decorator

ses_backends = {"global": ses_backend}
mock_ses = base_decorator(ses_backends)
