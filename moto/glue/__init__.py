from .models import glue_backend

glue_backends = {"global": glue_backend}
mock_glue = glue_backend.decorator
