from ..core.models import base_decorator
from .models import sagemaker_backends

sagemaker_backend = sagemaker_backends["us-east-1"]
mock_sagemaker = base_decorator(sagemaker_backends)
