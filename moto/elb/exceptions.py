from moto.core.exceptions import RESTError


class ELBClientError(RESTError):
    code = 400

    def __init__(self, error_type, message):
        super().__init__(error_type, message, template="wrapped_single_error")


class DuplicateTagKeysError(ELBClientError):
    def __init__(self, cidr):
        super().__init__(
            "DuplicateTagKeys", "Tag key was specified more than once: {0}".format(cidr)
        )


class CertificateNotFoundException(ELBClientError):
    def __init__(self):
        super().__init__(
            "CertificateNotFoundException", "Supplied certificate was not found"
        )


class LoadBalancerNotFoundError(ELBClientError):
    def __init__(self, cidr):
        super().__init__(
            "LoadBalancerNotFound",
            "The specified load balancer does not exist: {0}".format(cidr),
        )


class PolicyNotFoundError(ELBClientError):
    def __init__(self):
        super().__init__(
            "PolicyNotFound", "There is no policy with name . for load balancer ."
        )


class TooManyTagsError(ELBClientError):
    def __init__(self):
        super().__init__(
            "LoadBalancerNotFound",
            "The quota for the number of tags that can be assigned to a load balancer has been reached",
        )


class BadHealthCheckDefinition(ELBClientError):
    def __init__(self):
        super().__init__(
            "ValidationError",
            "HealthCheck Target must begin with one of HTTP, TCP, HTTPS, SSL",
        )


class DuplicateListenerError(ELBClientError):
    def __init__(self, name, port):
        super().__init__(
            "DuplicateListener",
            "A listener already exists for {0} with LoadBalancerPort {1}, but with a different InstancePort, Protocol, or SSLCertificateId".format(
                name, port
            ),
        )


class DuplicateLoadBalancerName(ELBClientError):
    def __init__(self, name):
        super().__init__(
            "DuplicateLoadBalancerName",
            "The specified load balancer name already exists for this account: {0}".format(
                name
            ),
        )


class EmptyListenersError(ELBClientError):
    def __init__(self):
        super().__init__("ValidationError", "Listeners cannot be empty")


class InvalidSecurityGroupError(ELBClientError):
    def __init__(self):
        super().__init__(
            "ValidationError",
            "One or more of the specified security groups do not exist.",
        )
