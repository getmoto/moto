from .models import sts_backend

sts_backends = {"global": sts_backend}
mock_sts = sts_backend.decorator
