from .models import sagemaker_backends

sagemaker_backend = sagemaker_backends["us-east-1"]
mock_sagemaker = sagemaker_backend.decorator
