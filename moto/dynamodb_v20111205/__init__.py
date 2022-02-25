from .models import dynamodb_backend

"""
An older API version of DynamoDB.
Please see the corresponding tests (tests/test_dynamodb_v20111205) on how to invoke this API.
"""

dynamodb_backends = {"global": dynamodb_backend}
mock_dynamodb = dynamodb_backend.decorator
