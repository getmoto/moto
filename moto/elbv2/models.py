from __future__ import unicode_literals

import datetime
import re
from jinja2 import Template
from botocore.exceptions import ParamValidationError
from moto.compat import OrderedDict
from moto.core.exceptions import RESTError
from moto.core import BaseBackend, BaseModel, CloudFormationModel
from moto.core.utils import camelcase_to_underscores, underscores_to_camelcase
from moto.ec2.models import ec2_backends
from moto.acm.models import acm_backends
from .utils import make_arn_for_target_group
from .utils import make_arn_for_load_balancer
from .exceptions import (
    DuplicateLoadBalancerName,
    DuplicateListenerError,
    DuplicateTargetGroupName,
    InvalidTargetError,
    ListenerNotFoundError,
    LoadBalancerNotFoundError,
    SubnetNotFoundError,
    TargetGroupNotFoundError,
    TooManyTagsError,
    PriorityInUseError,
    InvalidConditionFieldError,
    InvalidConditionValueError,
    InvalidActionTypeError,
    ActionTargetGroupNotFoundError,
    InvalidDescribeRulesRequest,
    ResourceInUseError,
    RuleNotFoundError,
    DuplicatePriorityError,
    InvalidTargetGroupNameError,
    InvalidModifyRuleArgumentsError,
    InvalidStatusCodeActionTypeError,
    InvalidLoadBalancerActionException,
)


class FakeHealthStatus(BaseModel):
    def __init__(
        self, instance_id, port, health_port, status, reason=None, description=None
    ):
        self.instance_id = instance_id
        self.port = port
        self.health_port = health_port
        self.status = status
        self.reason = reason
        self.description = description


class FakeTargetGroup(CloudFormationModel):
    HTTP_CODE_REGEX = re.compile(r"(?:(?:\d+-\d+|\d+),?)+")

    def __init__(
        self,
        name,
        arn,
        vpc_id,
        protocol,
        port,
        healthcheck_protocol=None,
        healthcheck_port=None,
        healthcheck_path=None,
        healthcheck_interval_seconds=None,
        healthcheck_timeout_seconds=None,
        healthy_threshold_count=None,
        unhealthy_threshold_count=None,
        matcher=None,
        target_type=None,
    ):

        # TODO: default values differs when you add Network Load balancer
        self.name = name
        self.arn = arn
        self.vpc_id = vpc_id
        self.protocol = protocol
        self.port = port
        self.healthcheck_protocol = healthcheck_protocol or "HTTP"
        self.healthcheck_port = healthcheck_port or str(self.port)
        self.healthcheck_path = healthcheck_path or "/"
        self.healthcheck_interval_seconds = healthcheck_interval_seconds or 30
        self.healthcheck_timeout_seconds = healthcheck_timeout_seconds or 5
        self.healthy_threshold_count = healthy_threshold_count or 5
        self.unhealthy_threshold_count = unhealthy_threshold_count or 2
        self.load_balancer_arns = []
        self.tags = {}
        if matcher is None:
            self.matcher = {"HttpCode": "200"}
        else:
            self.matcher = matcher
        self.target_type = target_type

        self.attributes = {
            "deregistration_delay.timeout_seconds": 300,
            "stickiness.enabled": "false",
        }

        self.targets = OrderedDict()

    @property
    def physical_resource_id(self):
        return self.arn

    def register(self, targets):
        for target in targets:
            self.targets[target["id"]] = {
                "id": target["id"],
                "port": target.get("port", self.port),
            }

    def deregister(self, targets):
        for target in targets:
            t = self.targets.pop(target["id"], None)
            if not t:
                raise InvalidTargetError()

    def deregister_terminated_instances(self, instance_ids):
        for target_id in list(self.targets.keys()):
            if target_id in instance_ids:
                del self.targets[target_id]

    def add_tag(self, key, value):
        if len(self.tags) >= 10 and key not in self.tags:
            raise TooManyTagsError()
        self.tags[key] = value

    def health_for(self, target, ec2_backend):
        t = self.targets.get(target["id"])
        if t is None:
            raise InvalidTargetError()
        if t["id"].startswith("i-"):  # EC2 instance ID
            instance = ec2_backend.get_instance_by_id(t["id"])
            if instance.state == "stopped":
                return FakeHealthStatus(
                    t["id"],
                    t["port"],
                    self.healthcheck_port,
                    "unused",
                    "Target.InvalidState",
                    "Target is in the stopped state",
                )
        return FakeHealthStatus(t["id"], t["port"], self.healthcheck_port, "healthy")

    @staticmethod
    def cloudformation_name_type():
        return "Name"

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-elasticloadbalancingv2-targetgroup.html
        return "AWS::ElasticLoadBalancingV2::TargetGroup"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        properties = cloudformation_json["Properties"]

        elbv2_backend = elbv2_backends[region_name]

        vpc_id = properties.get("VpcId")
        protocol = properties.get("Protocol")
        port = properties.get("Port")
        healthcheck_protocol = properties.get("HealthCheckProtocol")
        healthcheck_port = properties.get("HealthCheckPort")
        healthcheck_path = properties.get("HealthCheckPath")
        healthcheck_interval_seconds = properties.get("HealthCheckIntervalSeconds")
        healthcheck_timeout_seconds = properties.get("HealthCheckTimeoutSeconds")
        healthy_threshold_count = properties.get("HealthyThresholdCount")
        unhealthy_threshold_count = properties.get("UnhealthyThresholdCount")
        matcher = properties.get("Matcher")
        target_type = properties.get("TargetType")

        target_group = elbv2_backend.create_target_group(
            name=resource_name,
            vpc_id=vpc_id,
            protocol=protocol,
            port=port,
            healthcheck_protocol=healthcheck_protocol,
            healthcheck_port=healthcheck_port,
            healthcheck_path=healthcheck_path,
            healthcheck_interval_seconds=healthcheck_interval_seconds,
            healthcheck_timeout_seconds=healthcheck_timeout_seconds,
            healthy_threshold_count=healthy_threshold_count,
            unhealthy_threshold_count=unhealthy_threshold_count,
            matcher=matcher,
            target_type=target_type,
        )
        return target_group


class FakeListener(CloudFormationModel):
    def __init__(
        self,
        load_balancer_arn,
        arn,
        protocol,
        port,
        ssl_policy,
        certificate,
        default_actions,
    ):
        self.load_balancer_arn = load_balancer_arn
        self.arn = arn
        self.protocol = protocol.upper()
        self.port = port
        self.ssl_policy = ssl_policy
        self.certificate = certificate
        self.certificates = [certificate] if certificate is not None else []
        self.default_actions = default_actions
        self._non_default_rules = []
        self._default_rule = FakeRule(
            listener_arn=self.arn,
            conditions=[],
            priority="default",
            actions=default_actions,
            is_default=True,
        )

    @property
    def physical_resource_id(self):
        return self.arn

    @property
    def rules(self):
        return self._non_default_rules + [self._default_rule]

    def remove_rule(self, rule):
        self._non_default_rules.remove(rule)

    def register(self, rule):
        self._non_default_rules.append(rule)
        self._non_default_rules = sorted(
            self._non_default_rules, key=lambda x: x.priority
        )

    @staticmethod
    def cloudformation_name_type():
        return None

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-elasticloadbalancingv2-listener.html
        return "AWS::ElasticLoadBalancingV2::Listener"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        properties = cloudformation_json["Properties"]

        elbv2_backend = elbv2_backends[region_name]
        load_balancer_arn = properties.get("LoadBalancerArn")
        protocol = properties.get("Protocol")
        port = properties.get("Port")
        ssl_policy = properties.get("SslPolicy")
        certificates = properties.get("Certificates")
        # transform default actions to confirm with the rest of the code and XML templates
        if "DefaultActions" in properties:
            default_actions = []
            for i, action in enumerate(properties["DefaultActions"]):
                action_type = action["Type"]
                if action_type == "forward":
                    default_actions.append(
                        {
                            "type": action_type,
                            "target_group_arn": action["TargetGroupArn"],
                        }
                    )
                elif action_type in [
                    "redirect",
                    "authenticate-cognito",
                    "fixed-response",
                ]:
                    redirect_action = {"type": action_type}
                    key = (
                        underscores_to_camelcase(
                            action_type.capitalize().replace("-", "_")
                        )
                        + "Config"
                    )
                    for redirect_config_key, redirect_config_value in action[
                        key
                    ].items():
                        # need to match the output of _get_list_prefix
                        redirect_action[
                            camelcase_to_underscores(key)
                            + "._"
                            + camelcase_to_underscores(redirect_config_key)
                        ] = redirect_config_value
                    default_actions.append(redirect_action)
                else:
                    raise InvalidActionTypeError(action_type, i + 1)
        else:
            default_actions = None

        listener = elbv2_backend.create_listener(
            load_balancer_arn, protocol, port, ssl_policy, certificates, default_actions
        )
        return listener


class FakeAction(BaseModel):
    def __init__(self, data):
        self.data = data
        self.type = data.get("type")

    def to_xml(self):
        template = Template(
            """<Type>{{ action.type }}</Type>
            {% if action.type == "forward" %}
            <TargetGroupArn>{{ action.data["target_group_arn"] }}</TargetGroupArn>
            {% elif action.type == "redirect" %}
            <RedirectConfig>
                <Protocol>{{ action.data["redirect_config._protocol"] }}</Protocol>
                <Port>{{ action.data["redirect_config._port"] }}</Port>
                <StatusCode>{{ action.data["redirect_config._status_code"] }}</StatusCode>
            </RedirectConfig>
            {% elif action.type == "authenticate-cognito" %}
            <AuthenticateCognitoConfig>
                <UserPoolArn>{{ action.data["authenticate_cognito_config._user_pool_arn"] }}</UserPoolArn>
                <UserPoolClientId>{{ action.data["authenticate_cognito_config._user_pool_client_id"] }}</UserPoolClientId>
                <UserPoolDomain>{{ action.data["authenticate_cognito_config._user_pool_domain"] }}</UserPoolDomain>
            </AuthenticateCognitoConfig>
            {% elif action.type == "fixed-response" %}
             <FixedResponseConfig>
                <ContentType>{{ action.data["fixed_response_config._content_type"] }}</ContentType>
                <MessageBody>{{ action.data["fixed_response_config._message_body"] }}</MessageBody>
                <StatusCode>{{ action.data["fixed_response_config._status_code"] }}</StatusCode>
            </FixedResponseConfig>
            {% endif %}
            """
        )
        return template.render(action=self)


class FakeRule(BaseModel):
    def __init__(self, listener_arn, conditions, priority, actions, is_default):
        self.listener_arn = listener_arn
        self.arn = listener_arn.replace(":listener/", ":listener-rule/") + "/%s" % (
            id(self)
        )
        self.conditions = conditions
        self.priority = priority  # int or 'default'
        self.actions = actions
        self.is_default = is_default


class FakeBackend(BaseModel):
    def __init__(self, instance_port):
        self.instance_port = instance_port
        self.policy_names = []

    def __repr__(self):
        return "FakeBackend(inp: %s, policies: %s)" % (
            self.instance_port,
            self.policy_names,
        )


class FakeLoadBalancer(CloudFormationModel):
    VALID_ATTRS = {
        "access_logs.s3.enabled",
        "access_logs.s3.bucket",
        "access_logs.s3.prefix",
        "deletion_protection.enabled",
        "idle_timeout.timeout_seconds",
    }

    def __init__(
        self,
        name,
        security_groups,
        subnets,
        vpc_id,
        arn,
        dns_name,
        scheme="internet-facing",
    ):
        self.name = name
        self.created_time = datetime.datetime.now()
        self.scheme = scheme
        self.security_groups = security_groups
        self.subnets = subnets or []
        self.vpc_id = vpc_id
        self.listeners = OrderedDict()
        self.tags = {}
        self.arn = arn
        self.dns_name = dns_name

        self.stack = "ipv4"
        self.attrs = {
            "access_logs.s3.enabled": "false",
            "access_logs.s3.bucket": None,
            "access_logs.s3.prefix": None,
            "deletion_protection.enabled": "false",
            "idle_timeout.timeout_seconds": "60",
        }

    @property
    def physical_resource_id(self):
        return self.arn

    def add_tag(self, key, value):
        if len(self.tags) >= 10 and key not in self.tags:
            raise TooManyTagsError()
        self.tags[key] = value

    def list_tags(self):
        return self.tags

    def remove_tag(self, key):
        if key in self.tags:
            del self.tags[key]

    def delete(self, region):
        """ Not exposed as part of the ELB API - used for CloudFormation. """
        elbv2_backends[region].delete_load_balancer(self.arn)

    @staticmethod
    def cloudformation_name_type():
        return "Name"

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-elasticloadbalancingv2-loadbalancer.html
        return "AWS::ElasticLoadBalancingV2::LoadBalancer"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        properties = cloudformation_json["Properties"]

        elbv2_backend = elbv2_backends[region_name]

        security_groups = properties.get("SecurityGroups")
        subnet_ids = properties.get("Subnets")
        scheme = properties.get("Scheme", "internet-facing")

        load_balancer = elbv2_backend.create_load_balancer(
            resource_name, security_groups, subnet_ids, scheme=scheme
        )
        return load_balancer

    def get_cfn_attribute(self, attribute_name):
        """
        Implemented attributes:
        * DNSName
        * LoadBalancerName

        Not implemented:
        * CanonicalHostedZoneID
        * LoadBalancerFullName
        * SecurityGroups

        This method is similar to models.py:FakeLoadBalancer.get_cfn_attribute()
        """
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException

        not_implemented_yet = [
            "CanonicalHostedZoneID",
            "LoadBalancerFullName",
            "SecurityGroups",
        ]
        if attribute_name == "DNSName":
            return self.dns_name
        elif attribute_name == "LoadBalancerName":
            return self.name
        elif attribute_name in not_implemented_yet:
            raise NotImplementedError(
                '"Fn::GetAtt" : [ "{0}" , "%s" ]"' % attribute_name
            )
        else:
            raise UnformattedGetAttTemplateException()


class ELBv2Backend(BaseBackend):
    def __init__(self, region_name=None):
        self.region_name = region_name
        self.target_groups = OrderedDict()
        self.load_balancers = OrderedDict()

    @property
    def ec2_backend(self):
        """
        EC2 backend

        :return: EC2 Backend
        :rtype: moto.ec2.models.EC2Backend
        """
        return ec2_backends[self.region_name]

    @property
    def acm_backend(self):
        """
        ACM backend

        :return: ACM Backend
        :rtype: moto.acm.models.AWSCertificateManagerBackend
        """
        return acm_backends[self.region_name]

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def create_load_balancer(
        self, name, security_groups, subnet_ids, scheme="internet-facing"
    ):
        vpc_id = None
        subnets = []
        if not subnet_ids:
            raise SubnetNotFoundError()
        for subnet_id in subnet_ids:
            subnet = self.ec2_backend.get_subnet(subnet_id)
            if subnet is None:
                raise SubnetNotFoundError()
            subnets.append(subnet)

        vpc_id = subnets[0].vpc_id
        arn = make_arn_for_load_balancer(
            account_id=1, name=name, region_name=self.region_name
        )
        dns_name = "%s-1.%s.elb.amazonaws.com" % (name, self.region_name)

        if arn in self.load_balancers:
            raise DuplicateLoadBalancerName()

        new_load_balancer = FakeLoadBalancer(
            name=name,
            security_groups=security_groups,
            arn=arn,
            scheme=scheme,
            subnets=subnets,
            vpc_id=vpc_id,
            dns_name=dns_name,
        )
        self.load_balancers[arn] = new_load_balancer
        return new_load_balancer

    def create_rule(self, listener_arn, conditions, priority, actions):
        actions = [FakeAction(action) for action in actions]
        listeners = self.describe_listeners(None, [listener_arn])
        if not listeners:
            raise ListenerNotFoundError()
        listener = listeners[0]

        # validate conditions
        for condition in conditions:
            field = condition["field"]
            if field not in ["path-pattern", "host-header"]:
                raise InvalidConditionFieldError(field)

            values = condition["values"]
            if len(values) == 0:
                raise InvalidConditionValueError("A condition value must be specified")
            if len(values) > 1:
                raise InvalidConditionValueError(
                    "The '%s' field contains too many values; the limit is '1'" % field
                )

            # TODO: check pattern of value for 'host-header'
            # TODO: check pattern of value for 'path-pattern'

        # validate Priority
        for rule in listener.rules:
            if rule.priority == priority:
                raise PriorityInUseError()

        self._validate_actions(actions)

        # TODO: check for error 'TooManyRegistrationsForTargetId'
        # TODO: check for error 'TooManyRules'

        # create rule
        rule = FakeRule(listener.arn, conditions, priority, actions, is_default=False)
        listener.register(rule)
        return [rule]

    def _validate_actions(self, actions):
        # validate Actions
        target_group_arns = [
            target_group.arn for target_group in self.target_groups.values()
        ]
        for i, action in enumerate(actions):
            index = i + 1
            action_type = action.type
            if action_type == "forward":
                action_target_group_arn = action.data["target_group_arn"]
                if action_target_group_arn not in target_group_arns:
                    raise ActionTargetGroupNotFoundError(action_target_group_arn)
            elif action_type == "fixed-response":
                self._validate_fixed_response_action(action, i, index)
            elif action_type in ["redirect", "authenticate-cognito"]:
                pass
            else:
                raise InvalidActionTypeError(action_type, index)

    def _validate_fixed_response_action(self, action, i, index):
        status_code = action.data.get("fixed_response_config._status_code")
        if status_code is None:
            raise ParamValidationError(
                report='Missing required parameter in Actions[%s].FixedResponseConfig: "StatusCode"'
                % i
            )
        expression = r"^(2|4|5)\d\d$"
        if not re.match(expression, status_code):
            raise InvalidStatusCodeActionTypeError(
                "1 validation error detected: Value '{}' at 'actions.{}.member.fixedResponseConfig.statusCode' failed to satisfy constraint: \
Member must satisfy regular expression pattern: {}".format(
                    status_code, index, expression
                )
            )
        content_type = action.data["fixed_response_config._content_type"]
        if content_type and content_type not in [
            "text/plain",
            "text/css",
            "text/html",
            "application/javascript",
            "application/json",
        ]:
            raise InvalidLoadBalancerActionException(
                "The ContentType must be one of:'text/html', 'application/json', 'application/javascript', 'text/css', 'text/plain'"
            )

    def create_target_group(self, name, **kwargs):
        if len(name) > 32:
            raise InvalidTargetGroupNameError(
                "Target group name '{}' cannot be longer than '32' characters".format(
                    name
                )
            )
        if not re.match(r"^[a-zA-Z0-9\-]+$", name):
            raise InvalidTargetGroupNameError(
                "Target group name '{}' can only contain characters that are alphanumeric characters or hyphens(-)".format(
                    name
                )
            )

        # undocumented validation
        if not re.match(r"(?!.*--)(?!^-)(?!.*-$)^[A-Za-z0-9-]+$", name):
            raise InvalidTargetGroupNameError(
                "1 validation error detected: Value '%s' at 'targetGroup.targetGroupArn.targetGroupName' failed to satisfy constraint: Member must satisfy regular expression pattern: (?!.*--)(?!^-)(?!.*-$)^[A-Za-z0-9-]+$"
                % name
            )

        if name.startswith("-") or name.endswith("-"):
            raise InvalidTargetGroupNameError(
                "Target group name '%s' cannot begin or end with '-'" % name
            )
        for target_group in self.target_groups.values():
            if target_group.name == name:
                raise DuplicateTargetGroupName()

        valid_protocols = ["HTTPS", "HTTP", "TCP"]
        if (
            kwargs.get("healthcheck_protocol")
            and kwargs["healthcheck_protocol"] not in valid_protocols
        ):
            raise InvalidConditionValueError(
                "Value {} at 'healthCheckProtocol' failed to satisfy constraint: "
                "Member must satisfy enum value set: {}".format(
                    kwargs["healthcheck_protocol"], valid_protocols
                )
            )
        if kwargs.get("protocol") and kwargs["protocol"] not in valid_protocols:
            raise InvalidConditionValueError(
                "Value {} at 'protocol' failed to satisfy constraint: "
                "Member must satisfy enum value set: {}".format(
                    kwargs["protocol"], valid_protocols
                )
            )

        if (
            kwargs.get("matcher")
            and FakeTargetGroup.HTTP_CODE_REGEX.match(kwargs["matcher"]["HttpCode"])
            is None
        ):
            raise RESTError(
                "InvalidParameterValue",
                "HttpCode must be like 200 | 200-399 | 200,201 ...",
            )

        arn = make_arn_for_target_group(
            account_id=1, name=name, region_name=self.region_name
        )
        target_group = FakeTargetGroup(name, arn, **kwargs)
        self.target_groups[target_group.arn] = target_group
        return target_group

    def create_listener(
        self,
        load_balancer_arn,
        protocol,
        port,
        ssl_policy,
        certificate,
        default_actions,
    ):
        default_actions = [FakeAction(action) for action in default_actions]
        balancer = self.load_balancers.get(load_balancer_arn)
        if balancer is None:
            raise LoadBalancerNotFoundError()
        if port in balancer.listeners:
            raise DuplicateListenerError()

        self._validate_actions(default_actions)

        arn = load_balancer_arn.replace(":loadbalancer/", ":listener/") + "/%s%s" % (
            port,
            id(self),
        )
        listener = FakeListener(
            load_balancer_arn,
            arn,
            protocol,
            port,
            ssl_policy,
            certificate,
            default_actions,
        )
        balancer.listeners[listener.arn] = listener
        for action in default_actions:
            if action.type == "forward":
                target_group = self.target_groups[action.data["target_group_arn"]]
                target_group.load_balancer_arns.append(load_balancer_arn)

        return listener

    def describe_load_balancers(self, arns, names):
        balancers = self.load_balancers.values()
        arns = arns or []
        names = names or []
        if not arns and not names:
            return balancers

        matched_balancers = []
        matched_balancer = None

        for arn in arns:
            for balancer in balancers:
                if balancer.arn == arn:
                    matched_balancer = balancer
            if matched_balancer is None:
                raise LoadBalancerNotFoundError()
            elif matched_balancer not in matched_balancers:
                matched_balancers.append(matched_balancer)

        for name in names:
            for balancer in balancers:
                if balancer.name == name:
                    matched_balancer = balancer
            if matched_balancer is None:
                raise LoadBalancerNotFoundError()
            elif matched_balancer not in matched_balancers:
                matched_balancers.append(matched_balancer)

        return matched_balancers

    def describe_rules(self, listener_arn, rule_arns):
        if listener_arn is None and not rule_arns:
            raise InvalidDescribeRulesRequest(
                "You must specify either listener rule ARNs or a listener ARN"
            )
        if listener_arn is not None and rule_arns is not None:
            raise InvalidDescribeRulesRequest(
                "Listener rule ARNs and a listener ARN cannot be specified at the same time"
            )
        if listener_arn:
            listener = self.describe_listeners(None, [listener_arn])[0]
            return listener.rules

        # search for rule arns
        matched_rules = []
        for load_balancer_arn in self.load_balancers:
            listeners = self.load_balancers.get(load_balancer_arn).listeners.values()
            for listener in listeners:
                for rule in listener.rules:
                    if rule.arn in rule_arns:
                        matched_rules.append(rule)
        return matched_rules

    def describe_target_groups(self, load_balancer_arn, target_group_arns, names):
        if load_balancer_arn:
            if load_balancer_arn not in self.load_balancers:
                raise LoadBalancerNotFoundError()
            return [
                tg
                for tg in self.target_groups.values()
                if load_balancer_arn in tg.load_balancer_arns
            ]

        if target_group_arns:
            try:
                return [self.target_groups[arn] for arn in target_group_arns]
            except KeyError:
                raise TargetGroupNotFoundError()
        if names:
            matched = []
            for name in names:
                found = None
                for target_group in self.target_groups.values():
                    if target_group.name == name:
                        found = target_group
                if not found:
                    raise TargetGroupNotFoundError()
                matched.append(found)
            return matched

        return self.target_groups.values()

    def describe_listeners(self, load_balancer_arn, listener_arns):
        if load_balancer_arn:
            if load_balancer_arn not in self.load_balancers:
                raise LoadBalancerNotFoundError()
            return self.load_balancers.get(load_balancer_arn).listeners.values()

        matched = []
        for load_balancer in self.load_balancers.values():
            for listener_arn in listener_arns:
                listener = load_balancer.listeners.get(listener_arn)
                if not listener:
                    raise ListenerNotFoundError()
                matched.append(listener)
        return matched

    def delete_load_balancer(self, arn):
        self.load_balancers.pop(arn, None)

    def delete_rule(self, arn):
        for load_balancer_arn in self.load_balancers:
            listeners = self.load_balancers.get(load_balancer_arn).listeners.values()
            for listener in listeners:
                for rule in listener.rules:
                    if rule.arn == arn:
                        listener.remove_rule(rule)
                        return

        # should raise RuleNotFound Error according to the AWS API doc
        # however, boto3 does't raise error even if rule is not found

    def delete_target_group(self, target_group_arn):
        if target_group_arn not in self.target_groups:
            raise TargetGroupNotFoundError()

        target_group = self.target_groups[target_group_arn]
        if target_group:
            if self._any_listener_using(target_group_arn):
                raise ResourceInUseError(
                    "The target group '{}' is currently in use by a listener or a rule".format(
                        target_group_arn
                    )
                )
            del self.target_groups[target_group_arn]
            return target_group

    def delete_listener(self, listener_arn):
        for load_balancer in self.load_balancers.values():
            listener = load_balancer.listeners.pop(listener_arn, None)
            if listener:
                return listener
        raise ListenerNotFoundError()

    def modify_rule(self, rule_arn, conditions, actions):
        actions = [FakeAction(action) for action in actions]
        # if conditions or actions is empty list, do not update the attributes
        if not conditions and not actions:
            raise InvalidModifyRuleArgumentsError()
        rules = self.describe_rules(listener_arn=None, rule_arns=[rule_arn])
        if not rules:
            raise RuleNotFoundError()
        rule = rules[0]

        if conditions:
            for condition in conditions:
                field = condition["field"]
                if field not in ["path-pattern", "host-header"]:
                    raise InvalidConditionFieldError(field)

                values = condition["values"]
                if len(values) == 0:
                    raise InvalidConditionValueError(
                        "A condition value must be specified"
                    )
                if len(values) > 1:
                    raise InvalidConditionValueError(
                        "The '%s' field contains too many values; the limit is '1'"
                        % field
                    )
                # TODO: check pattern of value for 'host-header'
                # TODO: check pattern of value for 'path-pattern'

        # validate Actions
        self._validate_actions(actions)

        # TODO: check for error 'TooManyRegistrationsForTargetId'
        # TODO: check for error 'TooManyRules'

        # modify rule
        if conditions:
            rule.conditions = conditions
        if actions:
            rule.actions = actions
        return [rule]

    def register_targets(self, target_group_arn, instances):
        target_group = self.target_groups.get(target_group_arn)
        if target_group is None:
            raise TargetGroupNotFoundError()
        target_group.register(instances)

    def deregister_targets(self, target_group_arn, instances):
        target_group = self.target_groups.get(target_group_arn)
        if target_group is None:
            raise TargetGroupNotFoundError()
        target_group.deregister(instances)

    def describe_target_health(self, target_group_arn, targets):
        target_group = self.target_groups.get(target_group_arn)
        if target_group is None:
            raise TargetGroupNotFoundError()

        if not targets:
            targets = target_group.targets.values()
        return [target_group.health_for(target, self.ec2_backend) for target in targets]

    def set_rule_priorities(self, rule_priorities):
        # validate
        priorities = [rule_priority["priority"] for rule_priority in rule_priorities]
        for priority in set(priorities):
            if priorities.count(priority) > 1:
                raise DuplicatePriorityError(priority)

        # validate
        for rule_priority in rule_priorities:
            given_rule_arn = rule_priority["rule_arn"]
            priority = rule_priority["priority"]
            _given_rules = self.describe_rules(
                listener_arn=None, rule_arns=[given_rule_arn]
            )
            if not _given_rules:
                raise RuleNotFoundError()
            given_rule = _given_rules[0]
            listeners = self.describe_listeners(None, [given_rule.listener_arn])
            listener = listeners[0]
            for rule_in_listener in listener.rules:
                if rule_in_listener.priority == priority:
                    raise PriorityInUseError()
        # modify
        modified_rules = []
        for rule_priority in rule_priorities:
            given_rule_arn = rule_priority["rule_arn"]
            priority = rule_priority["priority"]
            _given_rules = self.describe_rules(
                listener_arn=None, rule_arns=[given_rule_arn]
            )
            if not _given_rules:
                raise RuleNotFoundError()
            given_rule = _given_rules[0]
            given_rule.priority = priority
            modified_rules.append(given_rule)
        return modified_rules

    def set_ip_address_type(self, arn, ip_type):
        if ip_type not in ("internal", "dualstack"):
            raise RESTError(
                "InvalidParameterValue",
                "IpAddressType must be either internal | dualstack",
            )

        balancer = self.load_balancers.get(arn)
        if balancer is None:
            raise LoadBalancerNotFoundError()

        if ip_type == "dualstack" and balancer.scheme == "internal":
            raise RESTError(
                "InvalidConfigurationRequest",
                "Internal load balancers cannot be dualstack",
            )

        balancer.stack = ip_type

    def set_security_groups(self, arn, sec_groups):
        balancer = self.load_balancers.get(arn)
        if balancer is None:
            raise LoadBalancerNotFoundError()

        # Check all security groups exist
        for sec_group_id in sec_groups:
            if self.ec2_backend.get_security_group_from_id(sec_group_id) is None:
                raise RESTError(
                    "InvalidSecurityGroup",
                    "Security group {0} does not exist".format(sec_group_id),
                )

        balancer.security_groups = sec_groups

    def set_subnets(self, arn, subnets):
        balancer = self.load_balancers.get(arn)
        if balancer is None:
            raise LoadBalancerNotFoundError()

        subnet_objects = []
        sub_zone_list = {}
        for subnet in subnets:
            try:
                subnet = self.ec2_backend.get_subnet(subnet)

                if subnet.availability_zone in sub_zone_list:
                    raise RESTError(
                        "InvalidConfigurationRequest",
                        "More than 1 subnet cannot be specified for 1 availability zone",
                    )

                sub_zone_list[subnet.availability_zone] = subnet.id
                subnet_objects.append(subnet)
            except Exception:
                raise SubnetNotFoundError()

        if len(sub_zone_list) < 2:
            raise RESTError(
                "InvalidConfigurationRequest",
                "More than 1 availability zone must be specified",
            )

        balancer.subnets = subnet_objects

        return sub_zone_list.items()

    def modify_load_balancer_attributes(self, arn, attrs):
        balancer = self.load_balancers.get(arn)
        if balancer is None:
            raise LoadBalancerNotFoundError()

        for key in attrs:
            if key not in FakeLoadBalancer.VALID_ATTRS:
                raise RESTError(
                    "InvalidConfigurationRequest", "Key {0} not valid".format(key)
                )

        balancer.attrs.update(attrs)
        return balancer.attrs

    def describe_load_balancer_attributes(self, arn):
        balancer = self.load_balancers.get(arn)
        if balancer is None:
            raise LoadBalancerNotFoundError()

        return balancer.attrs

    def modify_target_group(
        self,
        arn,
        health_check_proto=None,
        health_check_port=None,
        health_check_path=None,
        health_check_interval=None,
        health_check_timeout=None,
        healthy_threshold_count=None,
        unhealthy_threshold_count=None,
        http_codes=None,
    ):
        target_group = self.target_groups.get(arn)
        if target_group is None:
            raise TargetGroupNotFoundError()

        if (
            http_codes is not None
            and FakeTargetGroup.HTTP_CODE_REGEX.match(http_codes) is None
        ):
            raise RESTError(
                "InvalidParameterValue",
                "HttpCode must be like 200 | 200-399 | 200,201 ...",
            )

        if http_codes is not None:
            target_group.matcher["HttpCode"] = http_codes
        if health_check_interval is not None:
            target_group.healthcheck_interval_seconds = health_check_interval
        if health_check_path is not None:
            target_group.healthcheck_path = health_check_path
        if health_check_port is not None:
            target_group.healthcheck_port = health_check_port
        if health_check_proto is not None:
            target_group.healthcheck_protocol = health_check_proto
        if health_check_timeout is not None:
            target_group.healthcheck_timeout_seconds = health_check_timeout
        if healthy_threshold_count is not None:
            target_group.healthy_threshold_count = healthy_threshold_count
        if unhealthy_threshold_count is not None:
            target_group.unhealthy_threshold_count = unhealthy_threshold_count

        return target_group

    def modify_listener(
        self,
        arn,
        port=None,
        protocol=None,
        ssl_policy=None,
        certificates=None,
        default_actions=None,
    ):
        default_actions = [FakeAction(action) for action in default_actions]
        for load_balancer in self.load_balancers.values():
            if arn in load_balancer.listeners:
                break
        else:
            raise ListenerNotFoundError()

        listener = load_balancer.listeners[arn]

        if port is not None:
            for listener_arn, current_listener in load_balancer.listeners.items():
                if listener_arn == arn:
                    continue
                if listener.port == port:
                    raise DuplicateListenerError()

            listener.port = port

        if protocol is not None:
            if protocol not in ("HTTP", "HTTPS", "TCP"):
                raise RESTError(
                    "UnsupportedProtocol",
                    "Protocol {0} is not supported".format(protocol),
                )

            # HTTPS checks
            if protocol == "HTTPS":
                # HTTPS

                # Might already be HTTPS so may not provide certs
                if certificates is None and listener.protocol != "HTTPS":
                    raise RESTError(
                        "InvalidConfigurationRequest",
                        "Certificates must be provided for HTTPS",
                    )

                # Check certificates exist
                if certificates is not None:
                    default_cert = None
                    all_certs = set()  # for SNI
                    for cert in certificates:
                        if cert["is_default"] == "true":
                            default_cert = cert["certificate_arn"]
                        try:
                            self.acm_backend.get_certificate(cert["certificate_arn"])
                        except Exception:
                            raise RESTError(
                                "CertificateNotFound",
                                "Certificate {0} not found".format(
                                    cert["certificate_arn"]
                                ),
                            )

                        all_certs.add(cert["certificate_arn"])

                    if default_cert is None:
                        raise RESTError(
                            "InvalidConfigurationRequest", "No default certificate"
                        )

                    listener.certificate = default_cert
                    listener.certificates = list(all_certs)

            listener.protocol = protocol

        if ssl_policy is not None:
            # Its already validated in responses.py
            listener.ssl_policy = ssl_policy

        if default_actions is not None and default_actions != []:
            # Is currently not validated
            listener.default_actions = default_actions

        return listener

    def _any_listener_using(self, target_group_arn):
        for load_balancer in self.load_balancers.values():
            for listener in load_balancer.listeners.values():
                for rule in listener.rules:
                    for action in rule.actions:
                        if action.data.get("target_group_arn") == target_group_arn:
                            return True
        return False

    def notify_terminate_instances(self, instance_ids):
        for target_group in self.target_groups.values():
            target_group.deregister_terminated_instances(instance_ids)


elbv2_backends = {}
for region in ec2_backends.keys():
    elbv2_backends[region] = ELBv2Backend(region)
