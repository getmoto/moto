from .models import databrew_backend

databrew_backends = {"global": databrew_backend}
mock_databrew = databrew_backend.decorator
