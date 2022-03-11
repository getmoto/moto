import requests

from . import IntegrationParser


class TypeHttpParser(IntegrationParser):
    """
    Parse invocations to a APIGateway resource with integration type HTTP
    """

    def invoke(self, request, integration):
        uri = integration["uri"]
        requests_func = getattr(requests, integration["httpMethod"].lower())
        response = requests_func(uri)
        return response.status_code, response.text
