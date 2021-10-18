from .models import iam_backend

iam_backends = {"global": iam_backend}
mock_iam = iam_backend.decorator
