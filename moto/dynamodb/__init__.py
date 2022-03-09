from moto.dynamodb.models import dynamodb_backends
from ..core.models import base_decorator

dynamodb_backend = dynamodb_backends["us-east-1"]
mock_dynamodb = base_decorator(dynamodb_backends)
