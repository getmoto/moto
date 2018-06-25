from __future__ import unicode_literals
from moto.core.exceptions import RESTError


class ServiceNotFoundException(RESTError):
    code = 400

    def __init__(self, service_name):
        super(ServiceNotFoundException, self).__init__(
            error_type="ServiceNotFoundException",
            message="The service {0} does not exist".format(service_name))
