import abc


class IntegrationParser:
    @abc.abstractmethod
    def invoke(self, request, integration):
        pass
