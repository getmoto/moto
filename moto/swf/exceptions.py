from __future__ import unicode_literals

from boto.exception import JSONResponseError


class SWFClientError(JSONResponseError):
    def __init__(self, message, __type):
        super(SWFClientError, self).__init__(
            400, "Bad Request",
            body={"message": message, "__type": __type}
        )


class SWFUnknownResourceFault(SWFClientError):
    def __init__(self, resource_type, resource_name):
        super(SWFUnknownResourceFault, self).__init__(
            "Unknown {}: {}".format(resource_type, resource_name),
            "com.amazonaws.swf.base.model#UnknownResourceFault")


class SWFDomainAlreadyExistsFault(SWFClientError):
    def __init__(self, domain_name):
        super(SWFDomainAlreadyExistsFault, self).__init__(
            domain_name,
            "com.amazonaws.swf.base.model#DomainAlreadyExistsFault")


class SWFDomainDeprecatedFault(SWFClientError):
    def __init__(self, domain_name):
        super(SWFDomainDeprecatedFault, self).__init__(
            domain_name,
            "com.amazonaws.swf.base.model#DomainDeprecatedFault")


class SWFSerializationException(JSONResponseError):
    def __init__(self):
        message = "class java.lang.Foo can not be converted to an String (not a real SWF exception)"
        __type = "com.amazonaws.swf.base.model#SerializationException"
        super(SWFSerializationException, self).__init__(
            400, "Bad Request",
            body={"Message": message, "__type": __type}
        )
