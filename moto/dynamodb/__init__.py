from __future__ import unicode_literals
from .models import dynamodb_backend

dynamodb_backends = {"global": dynamodb_backend}
mock_dynamodb = dynamodb_backend.decorator
mock_dynamodb_deprecated = dynamodb_backend.deprecated_decorator
