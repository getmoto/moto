from .models import sagemaker_backends
from ..core.models import base_decorator

sagemaker_backend = sagemaker_backends["us-east-1"]
mock_sagemaker = base_decorator(sagemaker_backends)
