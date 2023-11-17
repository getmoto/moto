from ..awslambda.models import (
    lambda_backends,
    BaseBackend,
    LambdaBackend,
)
from ..core import BackendDict
from typing import Any, Optional, Union


class LambdaSimpleBackend(BaseBackend):
    """
    Implements a Lambda-Backend that does not use Docker containers, will always succeed.
    Annotate your tests with `@mock_lambda_simple`-decorator to use this Lambda-implementation.
    """

    @property
    def backend(self) -> LambdaBackend:
        return lambda_backends[self.account_id][self.region_name]

    def __getattribute__(self, name: str) -> Any:
        """
        Magic part that makes this class behave like a wrapper around the regular lambda_backend
        """
        if name in [
            "backend",
            "account_id",
            "region_name",
            "urls",
            "_url_module",
            "__class__",
            "url_bases",
        ]:
            return object.__getattribute__(self, name)
        if name in ["invoke", "invoke_async"]:

            def newfunc(*args: Any, **kwargs: Any) -> Any:
                attr = object.__getattribute__(self, name)
                return attr(*args, **kwargs)

            return newfunc
        else:
            return object.__getattribute__(self.backend, name)

    # pylint: disable=unused-argument
    def invoke(
        self,
        function_name: str,
        qualifier: str,
        body: Any,
        headers: Any,
        response_headers: Any,
    ) -> Optional[Union[str, bytes]]:

        if body:
            return str.encode(body)
        return b"Simple Lambda happy path OK"


lambda_simple_backends = BackendDict(LambdaSimpleBackend, "lambda")
