from .models import iam_backend
from ..core.models import base_decorator

iam_backends = {"global": iam_backend}
mock_iam = base_decorator(iam_backends)
