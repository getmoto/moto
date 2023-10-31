from moto.core.responses import BaseResponse
from ..awslambda.responses import LambdaResponse
from .models import lambda_simple_backends, LambdaBackend


class LambdaSimpleResponse(LambdaResponse):
    def __init__(self) -> None:
        super().__init__(service_name="awslambda_simple")

    @property
    def backend(self) -> LambdaBackend:
        return lambda_simple_backends[self.current_account][self.region]
