from . import IntegrationParser


class TypeUnknownParser(IntegrationParser):
    """
    Parse invocations to a APIGateway resource with an unknown integration type
    """

    def invoke(self, request, integration):
        _type = integration["type"]
        raise NotImplementedError("The {0} type has not been implemented".format(_type))
