from __future__ import unicode_literals
from .models import dynamodb_backend2

dynamodb_backends2 = {"global": dynamodb_backend2}
mock_dynamodb2 = dynamodb_backend2.decorator
mock_dynamodb2_deprecated = dynamodb_backend2.deprecated_decorator
