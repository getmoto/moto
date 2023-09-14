from moto.core import BaseBackend, BackendDict
from typing import Dict, List, Tuple


class SageMakerRuntimeBackend(BaseBackend):
    """Implementation of SageMakerRuntime APIs."""

    def __init__(self, region_name: str, account_id: str):
        super().__init__(region_name, account_id)
        self.results: Dict[str, Dict[bytes, Tuple[str, str, str, str]]] = {}
        self.results_queue: List[Tuple[str, str, str, str]] = []

    def invoke_endpoint(
        self, endpoint_name: str, unique_repr: bytes
    ) -> Tuple[str, str, str, str]:
        """
        This call will return static data by default.

        You can use a dedicated API to override this, by configuring a queue of expected results.

        A request to `get_query_results` will take the first result from that queue. Subsequent requests using the same details will return the same result. Other requests using a different QueryExecutionId will take the next result from the queue, or return static data if the queue is empty.

        Configuring this queue by making an HTTP request to `/moto-api/static/sagemaker/endpoint-results`. An example invocation looks like this:

        .. sourcecode:: python

            expected_results = {
                "account_id": "123456789012",  # This is the default - can be omitted
                "region": "us-east-1",  # This is the default - can be omitted
                "results": [
                    {
                         "Body": "first body",
                         "ContentType": "text/xml",
                         "InvokedProductionVariant": "prod",
                         "CustomAttributes": "my_attr",
                     },
                    # other results as required
                ],
            }
            requests.post(
                "http://motoapi.amazonaws.com:5000/moto-api/static/sagemaker/endpoint-results",
                json=expected_results,
            )

            client = boto3.client("sagemaker", region_name="us-east-1")
            details = client.invoke_endpoint(EndpointName="asdf", Body="qwer")

        """
        if endpoint_name not in self.results:
            self.results[endpoint_name] = {}
        if unique_repr in self.results[endpoint_name]:
            return self.results[endpoint_name][unique_repr]
        if self.results_queue:
            self.results[endpoint_name][unique_repr] = self.results_queue.pop(0)
        else:
            self.results[endpoint_name][unique_repr] = (
                "body",
                "content_type",
                "invoked_production_variant",
                "custom_attributes",
            )
        return self.results[endpoint_name][unique_repr]


sagemakerruntime_backends = BackendDict(SageMakerRuntimeBackend, "sagemaker-runtime")
