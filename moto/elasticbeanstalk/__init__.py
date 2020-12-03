from .models import eb_backends
from moto.core.models import base_decorator

mock_elasticbeanstalk = base_decorator(eb_backends)
