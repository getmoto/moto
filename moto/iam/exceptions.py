from __future__ import unicode_literals
from moto.core.exceptions import RESTError


class IAMNotFoundException(RESTError):
    code = 404

    def __init__(self, message):
        super(IAMNotFoundException, self).__init__(
            "NoSuchEntity", message)


class IAMConflictException(RESTError):
    code = 409

    def __init__(self, code='Conflict', message=""):
        super(IAMConflictException, self).__init__(
            code, message)


class IAMReportNotPresentException(RESTError):
    code = 410

    def __init__(self, message):
        super(IAMReportNotPresentException, self).__init__(
            "ReportNotPresent", message)
