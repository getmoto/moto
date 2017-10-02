from __future__ import unicode_literals

import datetime
import re
from moto.compat import OrderedDict
from moto.core import BaseBackend, BaseModel
from moto.ec2.models import ec2_backends
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
    RuleNotFoundError,
    DuplicatePriorityError,
    InvalidTargetGroupNameError,
    InvalidModifyRuleArgumentsError
)


class FakeHealthStatus(BaseModel):

    def __init__(self, instance_id, port, health_port, status, reason=None):
        self.instance_id = instance_id
        self.port = port
        self.health_port = health_port
        self.status = status
        self.reason = reason


class FakeTargetGroup(BaseModel):
    def __init__(self,
                 name,
                 arn,
                 vpc_id,
                 protocol,
                 port,
                 healthcheck_protocol,
                 healthcheck_port,
                 healthcheck_path,
                 healthcheck_interval_seconds,
                 healthcheck_timeout_seconds,
                 healthy_threshold_count,
                 unhealthy_threshold_count):
        self.name = name
        self.arn = arn
        self.vpc_id = vpc_id
        self.protocol = protocol
        self.port = port
        self.healthcheck_protocol = healthcheck_protocol
        self.healthcheck_port = healthcheck_port
        self.healthcheck_path = healthcheck_path
        self.healthcheck_interval_seconds = healthcheck_interval_seconds
        self.healthcheck_timeout_seconds = healthcheck_timeout_seconds
        self.healthy_threshold_count = healthy_threshold_count
        self.unhealthy_threshold_count = unhealthy_threshold_count
        self.load_balancer_arns = []
        self.tags = {}

        self.attributes = {
            'deregistration_delay.timeout_seconds': 300,
            'stickiness.enabled': 'false',
        }

        self.targets = OrderedDict()

    def register(self, targets):
        for target in targets:
            self.targets[target['id']] = {
                'id': target['id'],
                'port': target.get('port', self.port),
            }

    def deregister(self, targets):
        for target in targets:
            t = self.targets.pop(target['id'], None)
            if not t:
                raise InvalidTargetError()

    def add_tag(self, key, value):
        if len(self.tags) >= 10 and key not in self.tags:
            raise TooManyTagsError()
        self.tags[key] = value

    def health_for(self, target):
        t = self.targets.get(target['id'])
        if t is None:
            raise InvalidTargetError()
        return FakeHealthStatus(t['id'], t['port'], self.healthcheck_port, 'healthy')


class FakeListener(BaseModel):

    def __init__(self, load_balancer_arn, arn, protocol, port, ssl_policy, certificate, default_actions):
        self.load_balancer_arn = load_balancer_arn
        self.arn = arn
        self.protocol = protocol.upper()
        self.port = port
        self.ssl_policy = ssl_policy
        self.certificate = certificate
        self.default_actions = default_actions
        self._non_default_rules = []
        self._default_rule = FakeRule(
            listener_arn=self.arn,
            conditions=[],
            priority='default',
            actions=default_actions,
            is_default=True
        )

    @property
    def rules(self):
        return self._non_default_rules + [self._default_rule]

    def remove_rule(self, rule):
        self._non_default_rules.remove(rule)

    def register(self, rule):
        self._non_default_rules.append(rule)
        self._non_default_rules = sorted(self._non_default_rules, key=lambda x: x.priority)


class FakeRule(BaseModel):

    def __init__(self, listener_arn, conditions, priority, actions, is_default):
        self.listener_arn = listener_arn
        self.arn = listener_arn.replace(':listener/', ':listener-rule/') + "/%s" % (id(self))
        self.conditions = conditions
        self.priority = priority  # int or 'default'
        self.actions = actions
        self.is_default = is_default


class FakeBackend(BaseModel):

    def __init__(self, instance_port):
        self.instance_port = instance_port
        self.policy_names = []

    def __repr__(self):
        return "FakeBackend(inp: %s, policies: %s)" % (self.instance_port, self.policy_names)


class FakeLoadBalancer(BaseModel):

    def __init__(self, name, security_groups, subnets, vpc_id, arn, dns_name, scheme='internet-facing'):
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

    @property
    def physical_resource_id(self):
        return self.name

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
        ''' Not exposed as part of the ELB API - used for CloudFormation. '''
        elbv2_backends[region].delete_load_balancer(self.arn)


class ELBv2Backend(BaseBackend):

    def __init__(self, region_name=None):
        self.region_name = region_name
        self.target_groups = OrderedDict()
        self.load_balancers = OrderedDict()

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def create_load_balancer(self, name, security_groups, subnet_ids, scheme='internet-facing'):
        vpc_id = None
        ec2_backend = ec2_backends[self.region_name]
        subnets = []
        if not subnet_ids:
            raise SubnetNotFoundError()
        for subnet_id in subnet_ids:
            subnet = ec2_backend.get_subnet(subnet_id)
            if subnet is None:
                raise SubnetNotFoundError()
            subnets.append(subnet)

        vpc_id = subnets[0].vpc_id
        arn = "arn:aws:elasticloadbalancing:%s:1:loadbalancer/%s/50dc6c495c0c9188" % (self.region_name, name)
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
            dns_name=dns_name)
        self.load_balancers[arn] = new_load_balancer
        return new_load_balancer

    def create_rule(self, listener_arn, conditions, priority, actions):
        listeners = self.describe_listeners(None, [listener_arn])
        if not listeners:
            raise ListenerNotFoundError()
        listener = listeners[0]

        # validate conditions
        for condition in conditions:
            field = condition['field']
            if field not in ['path-pattern', 'host-header']:
                raise InvalidConditionFieldError(field)

            values = condition['values']
            if len(values) == 0:
                raise InvalidConditionValueError('A condition value must be specified')
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

        # validate Actions
        target_group_arns = [target_group.arn for target_group in self.target_groups.values()]
        for i, action in enumerate(actions):
            index = i + 1
            action_type = action['type']
            if action_type not in ['forward']:
                raise InvalidActionTypeError(action_type, index)
            action_target_group_arn = action['target_group_arn']
            if action_target_group_arn not in target_group_arns:
                raise ActionTargetGroupNotFoundError(action_target_group_arn)

        # TODO: check for error 'TooManyRegistrationsForTargetId'
        # TODO: check for error 'TooManyRules'

        # create rule
        rule = FakeRule(listener.arn, conditions, priority, actions, is_default=False)
        listener.register(rule)
        return [rule]

    def create_target_group(self, name, **kwargs):
        if len(name) > 32:
            raise InvalidTargetGroupNameError(
                "Target group name '%s' cannot be longer than '32' characters" % name
            )
        if not re.match('^[a-zA-Z0-9\-]+$', name):
            raise InvalidTargetGroupNameError(
                "Target group name '%s' can only contain characters that are alphanumeric characters or hyphens(-)" % name
            )

        # undocumented validation
        if not re.match('(?!.*--)(?!^-)(?!.*-$)^[A-Za-z0-9-]+$', name):
            raise InvalidTargetGroupNameError(
                "1 validation error detected: Value '%s' at 'targetGroup.targetGroupArn.targetGroupName' failed to satisfy constraint: Member must satisfy regular expression pattern: (?!.*--)(?!^-)(?!.*-$)^[A-Za-z0-9-]+$" % name
            )

        if name.startswith('-') or name.endswith('-'):
            raise InvalidTargetGroupNameError(
                "Target group name '%s' cannot begin or end with '-'" % name
            )
        for target_group in self.target_groups.values():
            if target_group.name == name:
                raise DuplicateTargetGroupName()

        arn = "arn:aws:elasticloadbalancing:%s:1:targetgroup/%s/50dc6c495c0c9188" % (self.region_name, name)
        target_group = FakeTargetGroup(name, arn, **kwargs)
        self.target_groups[target_group.arn] = target_group
        return target_group

    def create_listener(self, load_balancer_arn, protocol, port, ssl_policy, certificate, default_actions):
        balancer = self.load_balancers.get(load_balancer_arn)
        if balancer is None:
            raise LoadBalancerNotFoundError()
        if port in balancer.listeners:
            raise DuplicateListenerError()

        arn = load_balancer_arn.replace(':loadbalancer/', ':listener/') + "/%s%s" % (port, id(self))
        listener = FakeListener(load_balancer_arn, arn, protocol, port, ssl_policy, certificate, default_actions)
        balancer.listeners[listener.arn] = listener
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
                'Listener rule ARNs and a listener ARN cannot be specified at the same time'
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
            return [tg for tg in self.target_groups.values()
                    if load_balancer_arn in tg.load_balancer_arns]

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
        target_group = self.target_groups.pop(target_group_arn, None)
        if target_group:
            return target_group
        raise TargetGroupNotFoundError()

    def delete_listener(self, listener_arn):
        for load_balancer in self.load_balancers.values():
            listener = load_balancer.listeners.pop(listener_arn, None)
            if listener:
                return listener
        raise ListenerNotFoundError()

    def modify_rule(self, rule_arn, conditions, actions):
        # if conditions or actions is empty list, do not update the attributes
        if not conditions and not actions:
            raise InvalidModifyRuleArgumentsError()
        rules = self.describe_rules(listener_arn=None, rule_arns=[rule_arn])
        if not rules:
            raise RuleNotFoundError()
        rule = rules[0]

        if conditions:
            for condition in conditions:
                field = condition['field']
                if field not in ['path-pattern', 'host-header']:
                    raise InvalidConditionFieldError(field)

                values = condition['values']
                if len(values) == 0:
                    raise InvalidConditionValueError('A condition value must be specified')
                if len(values) > 1:
                    raise InvalidConditionValueError(
                        "The '%s' field contains too many values; the limit is '1'" % field
                    )
                # TODO: check pattern of value for 'host-header'
                # TODO: check pattern of value for 'path-pattern'

        # validate Actions
        target_group_arns = [target_group.arn for target_group in self.target_groups.values()]
        if actions:
            for i, action in enumerate(actions):
                index = i + 1
                action_type = action['type']
                if action_type not in ['forward']:
                    raise InvalidActionTypeError(action_type, index)
                action_target_group_arn = action['target_group_arn']
                if action_target_group_arn not in target_group_arns:
                    raise ActionTargetGroupNotFoundError(action_target_group_arn)

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
        return [target_group.health_for(target) for target in targets]

    def set_rule_priorities(self, rule_priorities):
        # validate
        priorities = [rule_priority['priority'] for rule_priority in rule_priorities]
        for priority in set(priorities):
            if priorities.count(priority) > 1:
                raise DuplicatePriorityError(priority)

        # validate
        for rule_priority in rule_priorities:
            given_rule_arn = rule_priority['rule_arn']
            priority = rule_priority['priority']
            _given_rules = self.describe_rules(listener_arn=None, rule_arns=[given_rule_arn])
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
            given_rule_arn = rule_priority['rule_arn']
            priority = rule_priority['priority']
            _given_rules = self.describe_rules(listener_arn=None, rule_arns=[given_rule_arn])
            if not _given_rules:
                raise RuleNotFoundError()
            given_rule = _given_rules[0]
            given_rule.priority = priority
            modified_rules.append(given_rule)
        return modified_rules


elbv2_backends = {}
for region in ec2_backends.keys():
    elbv2_backends[region] = ELBv2Backend(region)
