from moto.core.models import base_decorator

from .models import eb_backends

mock_elasticbeanstalk = base_decorator(eb_backends)
