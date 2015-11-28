from __future__ import unicode_literals

from boto.exception import JSONResponseError


class SWFClientError(JSONResponseError):
    def __init__(self, message, __type):
        super(SWFClientError, self).__init__(
            400, "Bad Request",
            body={"message": message, "__type": __type}
        )


class SWFUnknownResourceFault(SWFClientError):
    def __init__(self, resource_type, resource_name=None):
        if resource_name:
            message = "Unknown {0}: {1}".format(resource_type, resource_name)
        else:
            message = "Unknown {0}".format(resource_type)
        super(SWFUnknownResourceFault, self).__init__(
            message,
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
    def __init__(self, value):
        message = "class java.lang.Foo can not be converted to an String "
        message += " (not a real SWF exception ; happened on: {0})".format(value)
        __type = "com.amazonaws.swf.base.model#SerializationException"
        super(SWFSerializationException, self).__init__(
            400, "Bad Request",
            body={"Message": message, "__type": __type}
        )


class SWFTypeAlreadyExistsFault(SWFClientError):
    def __init__(self, _type):
        super(SWFTypeAlreadyExistsFault, self).__init__(
            "{0}=[name={1}, version={2}]".format(_type.__class__.__name__, _type.name, _type.version),
            "com.amazonaws.swf.base.model#TypeAlreadyExistsFault")


class SWFTypeDeprecatedFault(SWFClientError):
    def __init__(self, _type):
        super(SWFTypeDeprecatedFault, self).__init__(
            "{0}=[name={1}, version={2}]".format(_type.__class__.__name__, _type.name, _type.version),
            "com.amazonaws.swf.base.model#TypeDeprecatedFault")


class SWFWorkflowExecutionAlreadyStartedFault(JSONResponseError):
    def __init__(self):
        super(SWFWorkflowExecutionAlreadyStartedFault, self).__init__(
            400, "Bad Request",
            body={"__type": "com.amazonaws.swf.base.model#WorkflowExecutionAlreadyStartedFault"}
        )


class SWFDefaultUndefinedFault(SWFClientError):
    def __init__(self, key):
        # TODO: move that into moto.core.utils maybe?
        words = key.split("_")
        key_camel_case = words.pop(0)
        for word in words:
            key_camel_case += word.capitalize()
        super(SWFDefaultUndefinedFault, self).__init__(
            key_camel_case, "com.amazonaws.swf.base.model#DefaultUndefinedFault"
        )


class SWFValidationException(SWFClientError):
    def __init__(self, message):
        super(SWFValidationException, self).__init__(
            message,
            "com.amazon.coral.validate#ValidationException"
        )


class SWFDecisionValidationException(SWFClientError):
    def __init__(self, problems):
        # messages
        messages = []
        for pb in problems:
            if pb["type"] == "null_value":
                messages.append(
                    "Value null at '%(where)s' failed to satisfy constraint: "\
                    "Member must not be null" % pb
                )
            elif pb["type"] == "bad_decision_type":
                messages.append(
                    "Value '%(value)s' at '%(where)s' failed to satisfy constraint: " \
                    "Member must satisfy enum value set: " \
                    "[%(possible_values)s]" % pb
                )
            else:
                raise ValueError(
                    "Unhandled decision constraint type: {0}".format(pb["type"])
                )
        # prefix
        count = len(problems)
        if count < 2:
            prefix = "{0} validation error detected: "
        else:
            prefix = "{0} validation errors detected: "
        super(SWFDecisionValidationException, self).__init__(
            prefix.format(count) + "; ".join(messages),
            "com.amazon.coral.validate#ValidationException"
        )


class SWFWorkflowExecutionClosedError(Exception):
    def __str__(self):
        return repr("Cannot change this object because the WorkflowExecution is closed")
