import requests
from typing import Tuple, Union
from . import IntegrationParser
from ..models import Integration


class TypeUnknownParser(IntegrationParser):
    """
    Parse invocations to a APIGateway resource with an unknown integration type
    """

    def invoke(
        self, request: requests.PreparedRequest, integration: Integration
    ) -> Tuple[int, Union[str, bytes]]:
        _type = integration.integration_type
        raise NotImplementedError(f"The {_type} type has not been implemented")
