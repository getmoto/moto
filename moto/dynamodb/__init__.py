from .models import dynamodb_backend

dynamodb_backends = {"global": dynamodb_backend}
mock_dynamodb = dynamodb_backend.decorator
