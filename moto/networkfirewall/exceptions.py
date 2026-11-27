"""Exceptions raised by the networkfirewall service."""

from moto.core.exceptions import ServiceException


class NetworkFirewallException(ServiceException):
    pass


class ResourceNotFoundException(NetworkFirewallException):
    code = "ResourceNotFoundException"

    def __init__(self, resource_id: str):
        super().__init__(f"NetworkFirewall not found: {resource_id}")
