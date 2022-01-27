from moto.core.exceptions import JsonRESTError


class SWFClientError(JsonRESTError):
    code = 400


class SWFUnknownResourceFault(SWFClientError):
    def __init__(self, resource_type, resource_name=None):
        if resource_name:
            message = "Unknown {0}: {1}".format(resource_type, resource_name)
        else:
            message = "Unknown {0}".format(resource_type)
        super().__init__("com.amazonaws.swf.base.model#UnknownResourceFault", message)


class SWFDomainAlreadyExistsFault(SWFClientError):
    def __init__(self, domain_name):
        super().__init__(
            "com.amazonaws.swf.base.model#DomainAlreadyExistsFault", domain_name
        )


class SWFDomainDeprecatedFault(SWFClientError):
    def __init__(self, domain_name):
        super().__init__(
            "com.amazonaws.swf.base.model#DomainDeprecatedFault", domain_name
        )


class SWFSerializationException(SWFClientError):
    def __init__(self, value):
        message = "class java.lang.Foo can not be converted to an String "
        message += " (not a real SWF exception ; happened on: {0})".format(value)
        __type = "com.amazonaws.swf.base.model#SerializationException"
        super().__init__(__type, message)


class SWFTypeAlreadyExistsFault(SWFClientError):
    def __init__(self, _type):
        super().__init__(
            "com.amazonaws.swf.base.model#TypeAlreadyExistsFault",
            "{0}=[name={1}, version={2}]".format(
                _type.__class__.__name__, _type.name, _type.version
            ),
        )


class SWFTypeDeprecatedFault(SWFClientError):
    def __init__(self, _type):
        super().__init__(
            "com.amazonaws.swf.base.model#TypeDeprecatedFault",
            "{0}=[name={1}, version={2}]".format(
                _type.__class__.__name__, _type.name, _type.version
            ),
        )


class SWFWorkflowExecutionAlreadyStartedFault(SWFClientError):
    def __init__(self):
        super().__init__(
            "com.amazonaws.swf.base.model#WorkflowExecutionAlreadyStartedFault",
            "Already Started",
        )


class SWFDefaultUndefinedFault(SWFClientError):
    def __init__(self, key):
        # TODO: move that into moto.core.utils maybe?
        words = key.split("_")
        key_camel_case = words.pop(0)
        for word in words:
            key_camel_case += word.capitalize()
        super().__init__(
            "com.amazonaws.swf.base.model#DefaultUndefinedFault", key_camel_case
        )


class SWFValidationException(SWFClientError):
    def __init__(self, message):
        super().__init__("com.amazon.coral.validate#ValidationException", message)


class SWFDecisionValidationException(SWFClientError):
    def __init__(self, problems):
        # messages
        messages = []
        for pb in problems:
            if pb["type"] == "null_value":
                messages.append(
                    "Value null at '%(where)s' failed to satisfy constraint: "
                    "Member must not be null" % pb
                )
            elif pb["type"] == "bad_decision_type":
                messages.append(
                    "Value '%(value)s' at '%(where)s' failed to satisfy constraint: "
                    "Member must satisfy enum value set: "
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
        super().__init__(
            "com.amazon.coral.validate#ValidationException",
            prefix.format(count) + "; ".join(messages),
        )


class SWFWorkflowExecutionClosedError(Exception):
    def __str__(self):
        return repr("Cannot change this object because the WorkflowExecution is closed")
