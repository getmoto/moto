from ..core.models import base_decorator
from .models import iam_backends

mock_iam = base_decorator(iam_backends)
