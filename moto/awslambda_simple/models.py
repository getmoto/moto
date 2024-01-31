from typing import Any, Optional, Union

from moto.awslambda.models import LambdaBackend
from moto.core.base_backend import BackendDict


class LambdaSimpleBackend(LambdaBackend):
    """
    Implements a Lambda-Backend that does not use Docker containers, will always succeed.
    Annotate your tests with `@mock_aws(config={"lambda": {"use_docker": False}}) to use this Lambda-implementation.
    """

    # pylint: disable=unused-argument
    def invoke(
        self,
        function_name: str,
        qualifier: Optional[str],
        body: Any,
        headers: Any,
        response_headers: Any,
    ) -> Optional[Union[str, bytes]]:

        if body:
            return str.encode(body)
        return b"Simple Lambda happy path OK"


lambda_simple_backends = BackendDict(LambdaSimpleBackend, "lambda")
