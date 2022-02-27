from .models import s3_backend

s3_backends = {"global": s3_backend}
mock_s3 = s3_backend.decorator
