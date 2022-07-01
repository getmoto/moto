from .models import dynamodb_backends
from ..core.models import base_decorator

"""
An older API version of DynamoDB.
Please see the corresponding tests (tests/test_dynamodb_v20111205) on how to invoke this API.
"""

mock_dynamodb = base_decorator(dynamodb_backends)
