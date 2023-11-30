from ..core.models import base_decorator
from .models import dynamodbstreams_backends

dynamodbstreams_backend = dynamodbstreams_backends["us-east-1"]
mock_dynamodbstreams = base_decorator(dynamodbstreams_backends)
