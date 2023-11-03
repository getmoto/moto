from ..awslambda.responses import LambdaResponse
from .models import lambda_simple_backends, LambdaBackend


class LambdaSimpleResponse(LambdaResponse):
    @property
    def backend(self) -> LambdaBackend:
        return lambda_simple_backends[self.current_account][self.region]
