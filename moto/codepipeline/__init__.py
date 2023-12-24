from ..core.models import base_decorator
from .models import codepipeline_backends

mock_codepipeline = base_decorator(codepipeline_backends)
