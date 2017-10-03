from __future__ import unicode_literals
from moto.core.exceptions import RESTError


class ELBClientError(RESTError):
    code = 400


class DuplicateTagKeysError(ELBClientError):

    def __init__(self, cidr):
        super(DuplicateTagKeysError, self).__init__(
            "DuplicateTagKeys",
            "Tag key was specified more than once: {0}"
            .format(cidr))


class LoadBalancerNotFoundError(ELBClientError):

    def __init__(self):
        super(LoadBalancerNotFoundError, self).__init__(
            "LoadBalancerNotFound",
            "The specified load balancer does not exist.")


class ListenerNotFoundError(ELBClientError):

    def __init__(self):
        super(ListenerNotFoundError, self).__init__(
            "ListenerNotFound",
            "The specified listener does not exist.")


class SubnetNotFoundError(ELBClientError):

    def __init__(self):
        super(SubnetNotFoundError, self).__init__(
            "SubnetNotFound",
            "The specified subnet does not exist.")


class TargetGroupNotFoundError(ELBClientError):

    def __init__(self):
        super(TargetGroupNotFoundError, self).__init__(
            "TargetGroupNotFound",
            "The specified target group does not exist.")


class TooManyTagsError(ELBClientError):

    def __init__(self):
        super(TooManyTagsError, self).__init__(
            "TooManyTagsError",
            "The quota for the number of tags that can be assigned to a load balancer has been reached")


class BadHealthCheckDefinition(ELBClientError):

    def __init__(self):
        super(BadHealthCheckDefinition, self).__init__(
            "ValidationError",
            "HealthCheck Target must begin with one of HTTP, TCP, HTTPS, SSL")


class DuplicateListenerError(ELBClientError):

    def __init__(self):
        super(DuplicateListenerError, self).__init__(
            "DuplicateListener",
            "A listener with the specified port already exists.")


class DuplicateLoadBalancerName(ELBClientError):

    def __init__(self):
        super(DuplicateLoadBalancerName, self).__init__(
            "DuplicateLoadBalancerName",
            "A load balancer with the specified name already exists.")


class DuplicateTargetGroupName(ELBClientError):

    def __init__(self):
        super(DuplicateTargetGroupName, self).__init__(
            "DuplicateTargetGroupName",
            "A target group with the specified name already exists.")


class InvalidTargetError(ELBClientError):

    def __init__(self):
        super(InvalidTargetError, self).__init__(
            "InvalidTarget",
            "The specified target does not exist or is not in the same VPC as the target group.")


class EmptyListenersError(ELBClientError):

    def __init__(self):
        super(EmptyListenersError, self).__init__(
            "ValidationError",
            "Listeners cannot be empty")


class PriorityInUseError(ELBClientError):

    def __init__(self):
        super(PriorityInUseError, self).__init__(
            "PriorityInUse",
            "The specified priority is in use.")


class InvalidConditionFieldError(ELBClientError):

    def __init__(self, invalid_name):
        super(InvalidConditionFieldError, self).__init__(
            "ValidationError",
            "Condition field '%s' must be one of '[path-pattern, host-header]" % (invalid_name))


class InvalidConditionValueError(ELBClientError):

    def __init__(self, msg):
        super(InvalidConditionValueError, self).__init__(
            "ValidationError", msg)


class InvalidActionTypeError(ELBClientError):

    def __init__(self, invalid_name, index):
        super(InvalidActionTypeError, self).__init__(
            "ValidationError",
            "1 validation error detected: Value '%s' at 'actions.%s.member.type' failed to satisfy constraint: Member must satisfy enum value set: [forward]" % (invalid_name, index)
        )


class ActionTargetGroupNotFoundError(ELBClientError):

    def __init__(self, arn):
        super(ActionTargetGroupNotFoundError, self).__init__(
            "TargetGroupNotFound",
            "Target group '%s' not found" % arn
        )


class InvalidDescribeRulesRequest(ELBClientError):

    def __init__(self, msg):
        super(InvalidDescribeRulesRequest, self).__init__(
            "ValidationError", msg
        )


class ResourceInUseError(ELBClientError):

    def __init__(self, msg="A specified resource is in use"):
        super(ResourceInUseError, self).__init__(
            "ResourceInUse", msg)


class RuleNotFoundError(ELBClientError):

    def __init__(self):
        super(RuleNotFoundError, self).__init__(
            "RuleNotFound",
            "The specified rule does not exist.")


class DuplicatePriorityError(ELBClientError):

    def __init__(self, invalid_value):
        super(DuplicatePriorityError, self).__init__(
            "ValidationError",
            "Priority '%s' was provided multiple times" % invalid_value)


class InvalidTargetGroupNameError(ELBClientError):

    def __init__(self, msg):
        super(InvalidTargetGroupNameError, self).__init__(
            "ValidationError", msg
        )


class InvalidModifyRuleArgumentsError(ELBClientError):

    def __init__(self):
        super(InvalidModifyRuleArgumentsError, self).__init__(
            "ValidationError",
            "Either conditions or actions must be specified"
        )
