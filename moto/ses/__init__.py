from .models import ses_backend

ses_backends = {"global": ses_backend}
mock_ses = ses_backend.decorator
