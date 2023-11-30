from ..core.models import base_decorator
from .models import codebuild_backends

mock_codebuild = base_decorator(codebuild_backends)
