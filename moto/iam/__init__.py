from .models import iam_backends
from ..core.models import base_decorator

mock_iam = base_decorator(iam_backends)
