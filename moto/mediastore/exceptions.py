from moto.core.exceptions import JsonRESTError


class MediaStoreClientError(JsonRESTError):
    code = 400


class ContainerNotFoundException(MediaStoreClientError):
    def __init__(self, msg=None):
        self.code = 400
        super(ContainerNotFoundException, self).__init__(
            "ContainerNotFoundException",
            msg or "The specified container does not exist",
        )


class ResourceNotFoundException(MediaStoreClientError):
    def __init__(self, msg=None):
        self.code = 400
        super(ResourceNotFoundException, self).__init__(
            "ResourceNotFoundException", msg or "The specified container does not exist"
        )


class PolicyNotFoundException(MediaStoreClientError):
    def __init__(self, msg=None):
        self.code = 400
        super(PolicyNotFoundException, self).__init__(
            "PolicyNotFoundException",
            msg or "The policy does not exist within the specfied container",
        )
