from ..awslambda.models import (
    lambda_backends,
    BaseBackend,
    LambdaBackend,
)
from ..core import BackendDict
from typing import Any, Optional, Union


class LambdaSimpleBackend(BaseBackend):
    """
    Implements a Lambda-Backend that does not use Docker containers. Submitted Jobs are marked as Success by default.

    Set the environment variable MOTO_SIMPLE_BATCH_FAIL_AFTER=0 to fail jobs immediately, or set this variable to a positive integer to control after how many seconds the job fails.

    Annotate your tests with `@mock_batch_simple`-decorator to use this Batch-implementation.
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

    def invoke(
        self,
        function_name: str,
        qualifier: str,
        body: Any,
        headers: Any,
        response_headers: Any,
    ) -> Optional[Union[str, bytes]]:

        return b"Happy lambda response"


lambda_simple_backends = BackendDict(LambdaSimpleBackend, "lambda")
