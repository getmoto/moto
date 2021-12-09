from moto.dynamodb2.models import dynamodb_backends as dynamodb_backends2
from ..core.models import base_decorator, deprecated_base_decorator

dynamodb_backend2 = dynamodb_backends2["us-east-1"]
mock_dynamodb2 = base_decorator(dynamodb_backends2)
mock_dynamodb2_deprecated = deprecated_base_decorator(dynamodb_backends2)
