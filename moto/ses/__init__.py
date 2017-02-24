from __future__ import unicode_literals
from .models import ses_backend

ses_backends = {"global": ses_backend}
mock_ses = ses_backend.decorator
mock_ses_deprecated = ses_backend.deprecated_decorator
