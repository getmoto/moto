from __future__ import unicode_literals
from .models import dynamodbstreams_backends
from ..core.models import base_decorator

dynamodbstreams_backend = dynamodbstreams_backends['us-east-1']
mock_dynamodbstreams = base_decorator(dynamodbstreams_backends)
