from __future__ import unicode_literals
from moto.core.responses import BaseResponse
from .models import elbv2_backends
from .exceptions import DuplicateTagKeysError
from .exceptions import LoadBalancerNotFoundError
from .exceptions import TargetGroupNotFoundError


class ELBV2Response(BaseResponse):

    @property
    def elbv2_backend(self):
        return elbv2_backends[self.region]

    def create_load_balancer(self):
        load_balancer_name = self._get_param('Name')
        subnet_ids = self._get_multi_param("Subnets.member")
        security_groups = self._get_multi_param("SecurityGroups.member")
        scheme = self._get_param('Scheme')

        load_balancer = self.elbv2_backend.create_load_balancer(
            name=load_balancer_name,
            security_groups=security_groups,
            subnet_ids=subnet_ids,
            scheme=scheme,
        )
        self._add_tags(load_balancer)
        template = self.response_template(CREATE_LOAD_BALANCER_TEMPLATE)
        return template.render(load_balancer=load_balancer)

    def create_rule(self):
        lister_arn = self._get_param('ListenerArn')
        _conditions = self._get_list_prefix('Conditions.member')
        conditions = []
        for _condition in _conditions:
            condition = {}
            condition['field'] = _condition['field']
            values = sorted(
                [e for e in _condition.items() if e[0].startswith('values.member')],
                key=lambda x: x[0]
            )
            condition['values'] = [e[1] for e in values]
            conditions.append(condition)
        priority = self._get_int_param('Priority')
        actions = self._get_list_prefix('Actions.member')
        rules = self.elbv2_backend.create_rule(
            listener_arn=lister_arn,
            conditions=conditions,
            priority=priority,
            actions=actions
        )
        template = self.response_template(CREATE_RULE_TEMPLATE)
        return template.render(rules=rules)

    def create_target_group(self):
        name = self._get_param('Name')
        vpc_id = self._get_param('VpcId')
        protocol = self._get_param('Protocol')
        port = self._get_param('Port')
        healthcheck_protocol = self._get_param('HealthCheckProtocol', 'HTTP')
        healthcheck_port = self._get_param('HealthCheckPort', 'traffic-port')
        healthcheck_path = self._get_param('HealthCheckPath', '/')
        healthcheck_interval_seconds = self._get_param('HealthCheckIntervalSeconds', '30')
        healthcheck_timeout_seconds = self._get_param('HealthCheckTimeoutSeconds', '5')
        healthy_threshold_count = self._get_param('HealthyThresholdCount', '5')
        unhealthy_threshold_count = self._get_param('UnhealthyThresholdCount', '2')

        target_group = self.elbv2_backend.create_target_group(
            name,
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
        )

        template = self.response_template(CREATE_TARGET_GROUP_TEMPLATE)
        return template.render(target_group=target_group)

    def create_listener(self):
        load_balancer_arn = self._get_param('LoadBalancerArn')
        protocol = self._get_param('Protocol')
        port = self._get_param('Port')
        ssl_policy = self._get_param('SslPolicy', 'ELBSecurityPolicy-2016-08')
        certificates = self._get_list_prefix('Certificates.member')
        if certificates:
            certificate = certificates[0].get('certificate_arn')
        else:
            certificate = None
        default_actions = self._get_list_prefix('DefaultActions.member')

        listener = self.elbv2_backend.create_listener(
            load_balancer_arn=load_balancer_arn,
            protocol=protocol,
            port=port,
            ssl_policy=ssl_policy,
            certificate=certificate,
            default_actions=default_actions)

        template = self.response_template(CREATE_LISTENER_TEMPLATE)
        return template.render(listener=listener)

    def describe_load_balancers(self):
        arns = self._get_multi_param("LoadBalancerArns.member")
        names = self._get_multi_param("Names.member")
        all_load_balancers = list(self.elbv2_backend.describe_load_balancers(arns, names))
        marker = self._get_param('Marker')
        all_names = [balancer.name for balancer in all_load_balancers]
        if marker:
            start = all_names.index(marker) + 1
        else:
            start = 0
        page_size = self._get_param('PageSize', 50)  # the default is 400, but using 50 to make testing easier
        load_balancers_resp = all_load_balancers[start:start + page_size]
        next_marker = None
        if len(all_load_balancers) > start + page_size:
            next_marker = load_balancers_resp[-1].name

        template = self.response_template(DESCRIBE_LOAD_BALANCERS_TEMPLATE)
        return template.render(load_balancers=load_balancers_resp, marker=next_marker)

    def describe_rules(self):
        listener_arn = self._get_param('ListenerArn')
        rule_arns = self._get_multi_param('RuleArns.member') if any(k for k in list(self.querystring.keys()) if k.startswith('RuleArns.member')) else None
        all_rules = self.elbv2_backend.describe_rules(listener_arn, rule_arns)
        all_arns = [rule.arn for rule in all_rules]
        page_size = self._get_int_param('PageSize', 50)  # set 50 for temporary

        marker = self._get_param('Marker')
        if marker:
            start = all_arns.index(marker) + 1
        else:
            start = 0
        rules_resp = all_rules[start:start + page_size]
        next_marker = None

        if len(all_rules) > start + page_size:
            next_marker = rules_resp[-1].arn
        template = self.response_template(DESCRIBE_RULES_TEMPLATE)
        return template.render(rules=rules_resp, marker=next_marker)

    def describe_target_groups(self):
        load_balancer_arn = self._get_param('LoadBalancerArn')
        target_group_arns = self._get_multi_param('TargetGroupArns.member')
        names = self._get_multi_param('Names.member')

        target_groups = self.elbv2_backend.describe_target_groups(load_balancer_arn, target_group_arns, names)
        template = self.response_template(DESCRIBE_TARGET_GROUPS_TEMPLATE)
        return template.render(target_groups=target_groups)

    def describe_target_group_attributes(self):
        target_group_arn = self._get_param('TargetGroupArn')
        target_group = self.elbv2_backend.target_groups.get(target_group_arn)
        if not target_group:
            raise TargetGroupNotFoundError()
        template = self.response_template(DESCRIBE_TARGET_GROUP_ATTRIBUTES_TEMPLATE)
        return template.render(attributes=target_group.attributes)

    def describe_listeners(self):
        load_balancer_arn = self._get_param('LoadBalancerArn')
        listener_arns = self._get_multi_param('ListenerArns.member')
        if not load_balancer_arn and not listener_arns:
            raise LoadBalancerNotFoundError()

        listeners = self.elbv2_backend.describe_listeners(load_balancer_arn, listener_arns)
        template = self.response_template(DESCRIBE_LISTENERS_TEMPLATE)
        return template.render(listeners=listeners)

    def delete_load_balancer(self):
        arn = self._get_param('LoadBalancerArn')
        self.elbv2_backend.delete_load_balancer(arn)
        template = self.response_template(DELETE_LOAD_BALANCER_TEMPLATE)
        return template.render()

    def delete_rule(self):
        arn = self._get_param('RuleArn')
        self.elbv2_backend.delete_rule(arn)
        template = self.response_template(DELETE_RULE_TEMPLATE)
        return template.render()

    def delete_target_group(self):
        arn = self._get_param('TargetGroupArn')
        self.elbv2_backend.delete_target_group(arn)
        template = self.response_template(DELETE_TARGET_GROUP_TEMPLATE)
        return template.render()

    def delete_listener(self):
        arn = self._get_param('ListenerArn')
        self.elbv2_backend.delete_listener(arn)
        template = self.response_template(DELETE_LISTENER_TEMPLATE)
        return template.render()

    def modify_rule(self):
        rule_arn = self._get_param('RuleArn')
        _conditions = self._get_list_prefix('Conditions.member')
        conditions = []
        for _condition in _conditions:
            condition = {}
            condition['field'] = _condition['field']
            values = sorted(
                [e for e in _condition.items() if e[0].startswith('values.member')],
                key=lambda x: x[0]
            )
            condition['values'] = [e[1] for e in values]
            conditions.append(condition)
        actions = self._get_list_prefix('Actions.member')
        rules = self.elbv2_backend.modify_rule(
            rule_arn=rule_arn,
            conditions=conditions,
            actions=actions
        )
        template = self.response_template(MODIFY_RULE_TEMPLATE)
        return template.render(rules=rules)

    def modify_target_group_attributes(self):
        target_group_arn = self._get_param('TargetGroupArn')
        target_group = self.elbv2_backend.target_groups.get(target_group_arn)
        attributes = {
            attr['key']: attr['value']
            for attr in self._get_list_prefix('Attributes.member')
        }
        target_group.attributes.update(attributes)
        if not target_group:
            raise TargetGroupNotFoundError()
        template = self.response_template(MODIFY_TARGET_GROUP_ATTRIBUTES_TEMPLATE)
        return template.render(attributes=attributes)

    def register_targets(self):
        target_group_arn = self._get_param('TargetGroupArn')
        targets = self._get_list_prefix('Targets.member')
        self.elbv2_backend.register_targets(target_group_arn, targets)

        template = self.response_template(REGISTER_TARGETS_TEMPLATE)
        return template.render()

    def deregister_targets(self):
        target_group_arn = self._get_param('TargetGroupArn')
        targets = self._get_list_prefix('Targets.member')
        self.elbv2_backend.deregister_targets(target_group_arn, targets)

        template = self.response_template(DEREGISTER_TARGETS_TEMPLATE)
        return template.render()

    def describe_target_health(self):
        target_group_arn = self._get_param('TargetGroupArn')
        targets = self._get_list_prefix('Targets.member')
        target_health_descriptions = self.elbv2_backend.describe_target_health(target_group_arn, targets)

        template = self.response_template(DESCRIBE_TARGET_HEALTH_TEMPLATE)
        return template.render(target_health_descriptions=target_health_descriptions)

    def set_rule_priorities(self):
        rule_priorities = self._get_list_prefix('RulePriorities.member')
        for rule_priority in rule_priorities:
            rule_priority['priority'] = int(rule_priority['priority'])
        rules = self.elbv2_backend.set_rule_priorities(rule_priorities)
        template = self.response_template(SET_RULE_PRIORITIES_TEMPLATE)
        return template.render(rules=rules)

    def add_tags(self):
        resource_arns = self._get_multi_param('ResourceArns.member')

        for arn in resource_arns:
            if ':targetgroup' in arn:
                resource = self.elbv2_backend.target_groups.get(arn)
                if not resource:
                    raise TargetGroupNotFoundError()
            elif ':loadbalancer' in arn:
                resource = self.elbv2_backend.load_balancers.get(arn)
                if not resource:
                    raise LoadBalancerNotFoundError()
            else:
                raise LoadBalancerNotFoundError()
            self._add_tags(resource)

        template = self.response_template(ADD_TAGS_TEMPLATE)
        return template.render()

    def remove_tags(self):
        resource_arns = self._get_multi_param('ResourceArns.member')
        tag_keys = self._get_multi_param('TagKeys.member')

        for arn in resource_arns:
            if ':targetgroup' in arn:
                resource = self.elbv2_backend.target_groups.get(arn)
                if not resource:
                    raise TargetGroupNotFoundError()
            elif ':loadbalancer' in arn:
                resource = self.elbv2_backend.load_balancers.get(arn)
                if not resource:
                    raise LoadBalancerNotFoundError()
            else:
                raise LoadBalancerNotFoundError()
            [resource.remove_tag(key) for key in tag_keys]

        template = self.response_template(REMOVE_TAGS_TEMPLATE)
        return template.render()

    def describe_tags(self):
        resource_arns = self._get_multi_param('ResourceArns.member')
        resources = []
        for arn in resource_arns:
            if ':targetgroup' in arn:
                resource = self.elbv2_backend.target_groups.get(arn)
                if not resource:
                    raise TargetGroupNotFoundError()
            elif ':loadbalancer' in arn:
                resource = self.elbv2_backend.load_balancers.get(arn)
                if not resource:
                    raise LoadBalancerNotFoundError()
            else:
                raise LoadBalancerNotFoundError()
            resources.append(resource)

        template = self.response_template(DESCRIBE_TAGS_TEMPLATE)
        return template.render(resources=resources)

    def _add_tags(self, resource):
        tag_values = []
        tag_keys = []

        for t_key, t_val in sorted(self.querystring.items()):
            if t_key.startswith('Tags.member.'):
                if t_key.split('.')[3] == 'Key':
                    tag_keys.extend(t_val)
                elif t_key.split('.')[3] == 'Value':
                    tag_values.extend(t_val)

        counts = {}
        for i in tag_keys:
            counts[i] = tag_keys.count(i)

        counts = sorted(counts.items(), key=lambda i: i[1], reverse=True)

        if counts and counts[0][1] > 1:
            # We have dupes...
            raise DuplicateTagKeysError(counts[0])

        for tag_key, tag_value in zip(tag_keys, tag_values):
            resource.add_tag(tag_key, tag_value)


ADD_TAGS_TEMPLATE = """<AddTagsResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2015-12-01/">
  <AddTagsResult/>
  <ResponseMetadata>
    <RequestId>360e81f7-1100-11e4-b6ed-0f30EXAMPLE</RequestId>
  </ResponseMetadata>
</AddTagsResponse>"""

REMOVE_TAGS_TEMPLATE = """<RemoveTagsResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2015-12-01/">
  <RemoveTagsResult/>
  <ResponseMetadata>
    <RequestId>360e81f7-1100-11e4-b6ed-0f30EXAMPLE</RequestId>
  </ResponseMetadata>
</RemoveTagsResponse>"""

DESCRIBE_TAGS_TEMPLATE = """<DescribeTagsResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2015-12-01/">
  <DescribeTagsResult>
    <TagDescriptions>
      {% for resource in resources %}
      <member>
        <ResourceArn>{{ resource.arn }}</ResourceArn>
        <Tags>
          {% for key, value in resource.tags.items() %}
          <member>
            <Value>{{ value }}</Value>
            <Key>{{ key }}</Key>
          </member>
          {% endfor %}
        </Tags>
      </member>
      {% endfor %}
    </TagDescriptions>
  </DescribeTagsResult>
  <ResponseMetadata>
    <RequestId>360e81f7-1100-11e4-b6ed-0f30EXAMPLE</RequestId>
  </ResponseMetadata>
</DescribeTagsResponse>"""


CREATE_LOAD_BALANCER_TEMPLATE = """<CreateLoadBalancerResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2015-12-01/">
  <CreateLoadBalancerResult>
    <LoadBalancers>
      <member>
        <LoadBalancerArn>{{ load_balancer.arn }}</LoadBalancerArn>
        <Scheme>{{ load_balancer.scheme }}</Scheme>
        <LoadBalancerName>{{ load_balancer.name }}</LoadBalancerName>
        <VpcId>{{ load_balancer.vpc_id }}</VpcId>
        <CanonicalHostedZoneId>Z2P70J7EXAMPLE</CanonicalHostedZoneId>
        <CreatedTime>{{ load_balancer.created_time }}</CreatedTime>
        <AvailabilityZones>
          {% for subnet in load_balancer.subnets %}
          <member>
            <SubnetId>{{ subnet.id }}</SubnetId>
            <ZoneName>{{ subnet.availability_zone }}</ZoneName>
          </member>
          {% endfor %}
        </AvailabilityZones>
        <SecurityGroups>
          {% for security_group in load_balancer.security_groups %}
          <member>{{ security_group }}</member>
          {% endfor %}
        </SecurityGroups>
        <DNSName>{{ load_balancer.dns_name }}</DNSName>
        <State>
          <Code>provisioning</Code>
        </State>
        <Type>application</Type>
      </member>
    </LoadBalancers>
  </CreateLoadBalancerResult>
  <ResponseMetadata>
    <RequestId>32d531b2-f2d0-11e5-9192-3fff33344cfa</RequestId>
  </ResponseMetadata>
</CreateLoadBalancerResponse>"""

CREATE_RULE_TEMPLATE = """<CreateRuleResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2015-12-01/">
  <CreateRuleResult>
    <Rules>
      {% for rule in rules %}
      <member>
        <IsDefault>{{ "true" if rule.is_default else "false" }}</IsDefault>
        <Conditions>
          {% for condition in rule.conditions %}
          <member>
            <Field>{{ condition["field"] }}</Field>
            <Values>
              {% for value in condition["values"] %}
              <member>{{ value }}</member>
              {% endfor %}
            </Values>
          </member>
          {% endfor %}
        </Conditions>
        <Priority>{{ rule.priority }}</Priority>
        <Actions>
          {% for action in rule.actions %}
          <member>
            <Type>{{ action["type"] }}</Type>
            <TargetGroupArn>{{ action["target_group_arn"] }}</TargetGroupArn>
          </member>
          {% endfor %}
        </Actions>
        <RuleArn>{{ rule.arn }}</RuleArn>
      </member>
      {% endfor %}
    </Rules>
  </CreateRuleResult>
  <ResponseMetadata>
    <RequestId>c5478c83-f397-11e5-bb98-57195a6eb84a</RequestId>
  </ResponseMetadata>
</CreateRuleResponse>"""

CREATE_TARGET_GROUP_TEMPLATE = """<CreateTargetGroupResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2015-12-01/">
  <CreateTargetGroupResult>
    <TargetGroups>
      <member>
        <TargetGroupArn>{{ target_group.arn }}</TargetGroupArn>
        <TargetGroupName>{{ target_group.name }}</TargetGroupName>
        <Protocol>{{ target_group.protocol }}</Protocol>
        <Port>{{ target_group.port }}</Port>
        <VpcId>{{ target_group.vpc_id }}</VpcId>
        <HealthCheckProtocol>{{ target_group.health_check_protocol }}</HealthCheckProtocol>
        <HealthCheckPort>{{ target_group.healthcheck_port }}</HealthCheckPort>
        <HealthCheckPath>{{ target_group.healthcheck_path }}</HealthCheckPath>
        <HealthCheckIntervalSeconds>{{ target_group.healthcheck_interval_seconds }}</HealthCheckIntervalSeconds>
        <HealthCheckTimeoutSeconds>{{ target_group.healthcheck_timeout_seconds }}</HealthCheckTimeoutSeconds>
        <HealthyThresholdCount>{{ target_group.healthy_threshold_count }}</HealthyThresholdCount>
        <UnhealthyThresholdCount>{{ target_group.unhealthy_threshold_count }}</UnhealthyThresholdCount>
        <Matcher>
          <HttpCode>200</HttpCode>
        </Matcher>
      </member>
    </TargetGroups>
  </CreateTargetGroupResult>
  <ResponseMetadata>
    <RequestId>b83fe90e-f2d5-11e5-b95d-3b2c1831fc26</RequestId>
  </ResponseMetadata>
</CreateTargetGroupResponse>"""

CREATE_LISTENER_TEMPLATE = """<CreateListenerResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2015-12-01/">
  <CreateListenerResult>
    <Listeners>
      <member>
        <LoadBalancerArn>{{ listener.load_balancer_arn }}</LoadBalancerArn>
        <Protocol>{{ listener.protocol }}</Protocol>
        {% if listener.certificate %}
        <Certificates>
          <member>
            <CertificateArn>{{ listener.certificate }}</CertificateArn>
          </member>
        </Certificates>
        {% endif %}
        <Port>{{ listener.port }}</Port>
        <SslPolicy>{{ listener.ssl_policy }}</SslPolicy>
        <ListenerArn>{{ listener.arn }}</ListenerArn>
        <DefaultActions>
          {% for action in listener.default_actions %}
          <member>
            <Type>{{ action.type }}</Type>
            <TargetGroupArn>{{ action.target_group_arn }}</TargetGroupArn>
          </member>
          {% endfor %}
        </DefaultActions>
      </member>
    </Listeners>
  </CreateListenerResult>
  <ResponseMetadata>
    <RequestId>97f1bb38-f390-11e5-b95d-3b2c1831fc26</RequestId>
  </ResponseMetadata>
</CreateListenerResponse>"""

DELETE_LOAD_BALANCER_TEMPLATE = """<DeleteLoadBalancerResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2015-12-01/">
  <DeleteLoadBalancerResult/>
  <ResponseMetadata>
    <RequestId>1549581b-12b7-11e3-895e-1334aEXAMPLE</RequestId>
  </ResponseMetadata>
</DeleteLoadBalancerResponse>"""

DELETE_RULE_TEMPLATE = """<DeleteRuleResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2015-12-01/">
  <DeleteRuleResult/>
  <ResponseMetadata>
    <RequestId>1549581b-12b7-11e3-895e-1334aEXAMPLE</RequestId>
  </ResponseMetadata>
</DeleteRuleResponse>"""

DELETE_TARGET_GROUP_TEMPLATE = """<DeleteTargetGroupResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2015-12-01/">
  <DeleteTargetGroupResult/>
  <ResponseMetadata>
    <RequestId>1549581b-12b7-11e3-895e-1334aEXAMPLE</RequestId>
  </ResponseMetadata>
</DeleteTargetGroupResponse>"""

DELETE_LISTENER_TEMPLATE = """<DeleteListenerResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2015-12-01/">
  <DeleteListenerResult/>
  <ResponseMetadata>
    <RequestId>1549581b-12b7-11e3-895e-1334aEXAMPLE</RequestId>
  </ResponseMetadata>
</DeleteListenerResponse>"""

DESCRIBE_LOAD_BALANCERS_TEMPLATE = """<DescribeLoadBalancersResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2015-12-01/">
  <DescribeLoadBalancersResult>
    <LoadBalancers>
      {% for load_balancer in load_balancers %}
      <member>
        <LoadBalancerArn>{{ load_balancer.arn }}</LoadBalancerArn>
        <Scheme>{{ load_balancer.scheme }}</Scheme>
        <LoadBalancerName>{{ load_balancer.name }}</LoadBalancerName>
        <VpcId>{{ load_balancer.vpc_id }}</VpcId>
        <CanonicalHostedZoneId>Z2P70J7EXAMPLE</CanonicalHostedZoneId>
        <CreatedTime>{{ load_balancer.created_time }}</CreatedTime>
        <AvailabilityZones>
          {% for subnet in load_balancer.subnets %}
          <member>
            <SubnetId>{{ subnet.id }}</SubnetId>
            <ZoneName>{{ subnet.availability_zone }}</ZoneName>
          </member>
          {% endfor %}
        </AvailabilityZones>
        <SecurityGroups>
          {% for security_group in load_balancer.security_groups %}
          <member>{{ security_group }}</member>
          {% endfor %}
        </SecurityGroups>
        <DNSName>{{ load_balancer.dns_name }}</DNSName>
        <State>
          <Code>provisioning</Code>
        </State>
        <Type>application</Type>
      </member>
      {% endfor %}
    </LoadBalancers>
    {% if marker %}
    <NextMarker>{{ marker }}</NextMarker>
    {% endif %}
  </DescribeLoadBalancersResult>
  <ResponseMetadata>
    <RequestId>f9880f01-7852-629d-a6c3-3ae2-666a409287e6dc0c</RequestId>
  </ResponseMetadata>
</DescribeLoadBalancersResponse>"""

DESCRIBE_RULES_TEMPLATE = """<DescribeRulesResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2015-12-01/">
  <DescribeRulesResult>
    <Rules>
      {% for rule in rules %}
      <member>
        <IsDefault>{{ "true" if rule.is_default else "false" }}</IsDefault>
        <Conditions>
          {% for condition in rule.conditions %}
          <member>
            <Field>{{ condition["field"] }}</Field>
            <Values>
              {% for value in condition["values"] %}
              <member>{{ value }}</member>
              {% endfor %}
            </Values>
          </member>
          {% endfor %}
        </Conditions>
        <Priority>{{ rule.priority }}</Priority>
        <Actions>
          {% for action in rule.actions %}
          <member>
            <Type>{{ action["type"] }}</Type>
            <TargetGroupArn>{{ action["target_group_arn"] }}</TargetGroupArn>
          </member>
          {% endfor %}
        </Actions>
        <RuleArn>{{ rule.arn }}</RuleArn>
      </member>
      {% endfor %}
    </Rules>
    {% if marker %}
    <NextMarker>{{ marker }}</NextMarker>
    {% endif %}
  </DescribeRulesResult>
  <ResponseMetadata>
    <RequestId>74926cf3-f3a3-11e5-b543-9f2c3fbb9bee</RequestId>
  </ResponseMetadata>
</DescribeRulesResponse>"""

DESCRIBE_TARGET_GROUPS_TEMPLATE = """<DescribeTargetGroupsResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2015-12-01/">
  <DescribeTargetGroupsResult>
    <TargetGroups>
      {% for target_group in target_groups %}
      <member>
        <TargetGroupArn>{{ target_group.arn }}</TargetGroupArn>
        <TargetGroupName>{{ target_group.name }}</TargetGroupName>
        <Protocol>{{ target_group.protocol }}</Protocol>
        <Port>{{ target_group.port }}</Port>
        <VpcId>{{ target_group.vpc_id }}</VpcId>
        <HealthCheckProtocol>{{ target_group.health_check_protocol }}</HealthCheckProtocol>
        <HealthCheckPort>{{ target_group.healthcheck_port }}</HealthCheckPort>
        <HealthCheckPath>{{ target_group.healthcheck_path }}</HealthCheckPath>
        <HealthCheckIntervalSeconds>{{ target_group.healthcheck_interval_seconds }}</HealthCheckIntervalSeconds>
        <HealthCheckTimeoutSeconds>{{ target_group.healthcheck_timeout_seconds }}</HealthCheckTimeoutSeconds>
        <HealthyThresholdCount>{{ target_group.healthy_threshold_count }}</HealthyThresholdCount>
        <UnhealthyThresholdCount>{{ target_group.unhealthy_threshold_count }}</UnhealthyThresholdCount>
        <Matcher>
          <HttpCode>200</HttpCode>
        </Matcher>
        <LoadBalancerArns>
          {% for load_balancer_arn in target_group.load_balancer_arns %}
          <member>{{ load_balancer_arn }}</member>
          {% endfor %}
        </LoadBalancerArns>
      </member>
      {% endfor %}
    </TargetGroups>
  </DescribeTargetGroupsResult>
  <ResponseMetadata>
    <RequestId>70092c0e-f3a9-11e5-ae48-cff02092876b</RequestId>
  </ResponseMetadata>
</DescribeTargetGroupsResponse>"""


DESCRIBE_TARGET_GROUP_ATTRIBUTES_TEMPLATE = """<DescribeTargetGroupAttributesResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2015-12-01/">
  <DescribeTargetGroupAttributesResult>
    <Attributes>
      {% for key, value in attributes.items() %}
      <member>
        <Key>{{ key }}</Key>
        <Value>{{ value }}</Value>
      </member>
      {% endfor %}
    </Attributes>
  </DescribeTargetGroupAttributesResult>
  <ResponseMetadata>
    <RequestId>70092c0e-f3a9-11e5-ae48-cff02092876b</RequestId>
  </ResponseMetadata>
</DescribeTargetGroupAttributesResponse>"""


DESCRIBE_LISTENERS_TEMPLATE = """<DescribeLoadBalancersResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2015-12-01/">
  <DescribeListenersResult>
    <Listeners>
      {% for listener in listeners %}
      <member>
        <LoadBalancerArn>{{ listener.load_balancer_arn }}</LoadBalancerArn>
        <Protocol>{{ listener.protocol }}</Protocol>
        {% if listener.certificate %}
        <Certificates>
          <member>
            <CertificateArn>{{ listener.certificate }}</CertificateArn>
          </member>
        </Certificates>
        {% endif %}
        <Port>{{ listener.port }}</Port>
        <SslPolicy>{{ listener.ssl_policy }}</SslPolicy>
        <ListenerArn>{{ listener.arn }}</ListenerArn>
        <DefaultActions>
          {% for action in listener.default_actions %}
          <member>
            <Type>{{ action.type }}</Type>
            <TargetGroupArn>{{ action.target_group_arn }}</TargetGroupArn>
          </member>
          {% endfor %}
        </DefaultActions>
      </member>
      {% endfor %}
    </Listeners>
  </DescribeListenersResult>
  <ResponseMetadata>
    <RequestId>65a3a7ea-f39c-11e5-b543-9f2c3fbb9bee</RequestId>
  </ResponseMetadata>
</DescribeLoadBalancersResponse>"""

CONFIGURE_HEALTH_CHECK_TEMPLATE = """<ConfigureHealthCheckResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2015-12-01/">
  <ConfigureHealthCheckResult>
    <HealthCheck>
      <Interval>{{ check.interval }}</Interval>
      <Target>{{ check.target }}</Target>
      <HealthyThreshold>{{ check.healthy_threshold }}</HealthyThreshold>
      <Timeout>{{ check.timeout }}</Timeout>
      <UnhealthyThreshold>{{ check.unhealthy_threshold }}</UnhealthyThreshold>
    </HealthCheck>
  </ConfigureHealthCheckResult>
  <ResponseMetadata>
    <RequestId>f9880f01-7852-629d-a6c3-3ae2-666a409287e6dc0c</RequestId>
  </ResponseMetadata>
</ConfigureHealthCheckResponse>"""

MODIFY_RULE_TEMPLATE = """<ModifyRuleResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2015-12-01/">
  <ModifyRuleResult>
    <Rules>
      {% for rule in rules %}
      <member>
        <IsDefault>{{ "true" if rule.is_default else "false" }}</IsDefault>
        <Conditions>
          {% for condition in rule.conditions %}
          <member>
            <Field>{{ condition["field"] }}</Field>
            <Values>
              {% for value in condition["values"] %}
              <member>{{ value }}</member>
              {% endfor %}
            </Values>
          </member>
          {% endfor %}
        </Conditions>
        <Priority>{{ rule.priority }}</Priority>
        <Actions>
          {% for action in rule.actions %}
          <member>
            <Type>{{ action["type"] }}</Type>
            <TargetGroupArn>{{ action["target_group_arn"] }}</TargetGroupArn>
          </member>
          {% endfor %}
        </Actions>
        <RuleArn>{{ rule.arn }}</RuleArn>
      </member>
      {% endfor %}
    </Rules>
  </ModifyRuleResult>
  <ResponseMetadata>
    <RequestId>c5478c83-f397-11e5-bb98-57195a6eb84a</RequestId>
  </ResponseMetadata>
</ModifyRuleResponse>"""

MODIFY_TARGET_GROUP_ATTRIBUTES_TEMPLATE = """<ModifyTargetGroupAttributesResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2015-12-01/">
  <ModifyTargetGroupAttributesResult>
    <Attributes>
      {% for key, value in attributes.items() %}
      <member>
        <Key>{{ key }}</Key>
        <Value>{{ value }}</Value>
      </member>
      {% endfor %}
    </Attributes>
  </ModifyTargetGroupAttributesResult>
  <ResponseMetadata>
    <RequestId>70092c0e-f3a9-11e5-ae48-cff02092876b</RequestId>
  </ResponseMetadata>
</ModifyTargetGroupAttributesResponse>"""

REGISTER_TARGETS_TEMPLATE = """<RegisterTargetsResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2015-12-01/">
  <RegisterTargetsResult>
  </RegisterTargetsResult>
  <ResponseMetadata>
    <RequestId>f9880f01-7852-629d-a6c3-3ae2-666a409287e6dc0c</RequestId>
  </ResponseMetadata>
</RegisterTargetsResponse>"""

DEREGISTER_TARGETS_TEMPLATE = """<DeregisterTargetsResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2015-12-01/">
  <DeregisterTargetsResult>
  </DeregisterTargetsResult>
  <ResponseMetadata>
    <RequestId>f9880f01-7852-629d-a6c3-3ae2-666a409287e6dc0c</RequestId>
  </ResponseMetadata>
</DeregisterTargetsResponse>"""

SET_LOAD_BALANCER_SSL_CERTIFICATE = """<SetLoadBalancerListenerSSLCertificateResponse xmlns="http://elasticloadbalan cing.amazonaws.com/doc/2015-12-01/">
 <SetLoadBalancerListenerSSLCertificateResult/>
<ResponseMetadata>
    <RequestId>83c88b9d-12b7-11e3-8b82-87b12EXAMPLE</RequestId>
</ResponseMetadata>
</SetLoadBalancerListenerSSLCertificateResponse>"""


DELETE_LOAD_BALANCER_LISTENERS = """<DeleteLoadBalancerListenersResponse xmlns="http://elasticloadbalan cing.amazonaws.com/doc/2015-12-01/">
 <DeleteLoadBalancerListenersResult/>
<ResponseMetadata>
    <RequestId>83c88b9d-12b7-11e3-8b82-87b12EXAMPLE</RequestId>
</ResponseMetadata>
</DeleteLoadBalancerListenersResponse>"""

DESCRIBE_ATTRIBUTES_TEMPLATE = """<DescribeLoadBalancerAttributesResponse  xmlns="http://elasticloadbalancing.amazonaws.com/doc/2015-12-01/">
  <DescribeLoadBalancerAttributesResult>
    <LoadBalancerAttributes>
      <AccessLog>
        <Enabled>{{ attributes.access_log.enabled }}</Enabled>
        {% if attributes.access_log.enabled %}
        <S3BucketName>{{ attributes.access_log.s3_bucket_name }}</S3BucketName>
        <S3BucketPrefix>{{ attributes.access_log.s3_bucket_prefix }}</S3BucketPrefix>
        <EmitInterval>{{ attributes.access_log.emit_interval }}</EmitInterval>
        {% endif %}
      </AccessLog>
      <ConnectionSettings>
        <IdleTimeout>{{ attributes.connecting_settings.idle_timeout }}</IdleTimeout>
      </ConnectionSettings>
      <CrossZoneLoadBalancing>
        <Enabled>{{ attributes.cross_zone_load_balancing.enabled }}</Enabled>
      </CrossZoneLoadBalancing>
      <ConnectionDraining>
        {% if attributes.connection_draining.enabled %}
        <Enabled>true</Enabled>
        <Timeout>{{ attributes.connection_draining.timeout }}</Timeout>
        {% else %}
        <Enabled>false</Enabled>
        {% endif %}
      </ConnectionDraining>
    </LoadBalancerAttributes>
  </DescribeLoadBalancerAttributesResult>
  <ResponseMetadata>
    <RequestId>83c88b9d-12b7-11e3-8b82-87b12EXAMPLE</RequestId>
  </ResponseMetadata>
</DescribeLoadBalancerAttributesResponse>
"""

MODIFY_ATTRIBUTES_TEMPLATE = """<ModifyLoadBalancerAttributesResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2015-12-01/">
  <ModifyLoadBalancerAttributesResult>
  <LoadBalancerName>{{ load_balancer.name }}</LoadBalancerName>
    <LoadBalancerAttributes>
      <AccessLog>
        <Enabled>{{ attributes.access_log.enabled }}</Enabled>
        {% if attributes.access_log.enabled %}
        <S3BucketName>{{ attributes.access_log.s3_bucket_name }}</S3BucketName>
        <S3BucketPrefix>{{ attributes.access_log.s3_bucket_prefix }}</S3BucketPrefix>
        <EmitInterval>{{ attributes.access_log.emit_interval }}</EmitInterval>
        {% endif %}
      </AccessLog>
      <ConnectionSettings>
        <IdleTimeout>{{ attributes.connecting_settings.idle_timeout }}</IdleTimeout>
      </ConnectionSettings>
      <CrossZoneLoadBalancing>
        <Enabled>{{ attributes.cross_zone_load_balancing.enabled }}</Enabled>
      </CrossZoneLoadBalancing>
      <ConnectionDraining>
        {% if attributes.connection_draining.enabled %}
        <Enabled>true</Enabled>
        <Timeout>{{ attributes.connection_draining.timeout }}</Timeout>
        {% else %}
        <Enabled>false</Enabled>
        {% endif %}
      </ConnectionDraining>
    </LoadBalancerAttributes>
  </ModifyLoadBalancerAttributesResult>
  <ResponseMetadata>
    <RequestId>83c88b9d-12b7-11e3-8b82-87b12EXAMPLE</RequestId>
  </ResponseMetadata>
</ModifyLoadBalancerAttributesResponse>
"""

CREATE_LOAD_BALANCER_POLICY_TEMPLATE = """<CreateLoadBalancerPolicyResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2015-12-01/">
  <CreateLoadBalancerPolicyResult/>
  <ResponseMetadata>
      <RequestId>83c88b9d-12b7-11e3-8b82-87b12EXAMPLE</RequestId>
  </ResponseMetadata>
</CreateLoadBalancerPolicyResponse>
"""

SET_LOAD_BALANCER_POLICIES_OF_LISTENER_TEMPLATE = """<SetLoadBalancerPoliciesOfListenerResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2015-12-01/">
    <SetLoadBalancerPoliciesOfListenerResult/>
    <ResponseMetadata>
        <RequestId>07b1ecbc-1100-11e3-acaf-dd7edEXAMPLE</RequestId>
    </ResponseMetadata>
</SetLoadBalancerPoliciesOfListenerResponse>
"""

SET_LOAD_BALANCER_POLICIES_FOR_BACKEND_SERVER_TEMPLATE = """<SetLoadBalancerPoliciesForBackendServerResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2015-12-01/">
    <SetLoadBalancerPoliciesForBackendServerResult/>
    <ResponseMetadata>
        <RequestId>0eb9b381-dde0-11e2-8d78-6ddbaEXAMPLE</RequestId>
    </ResponseMetadata>
</SetLoadBalancerPoliciesForBackendServerResponse>
"""

DESCRIBE_TARGET_HEALTH_TEMPLATE = """<DescribeTargetHealthResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2015-12-01/">
  <DescribeTargetHealthResult>
    <TargetHealthDescriptions>
      {% for target_health in target_health_descriptions %}
      <member>
        <HealthCheckPort>{{ target_health.health_port }}</HealthCheckPort>
        <TargetHealth>
          <State>{{ target_health.status }}</State>
        </TargetHealth>
        <Target>
          <Port>{{ target_health.port }}</Port>
          <Id>{{ target_health.instance_id }}</Id>
        </Target>
      </member>
      {% endfor %}
    </TargetHealthDescriptions>
  </DescribeTargetHealthResult>
  <ResponseMetadata>
    <RequestId>c534f810-f389-11e5-9192-3fff33344cfa</RequestId>
  </ResponseMetadata>
</DescribeTargetHealthResponse>"""

SET_RULE_PRIORITIES_TEMPLATE = """<SetRulePrioritiesResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2015-12-01/">
  <SetRulePrioritiesResult>
    <Rules>
      {% for rule in rules %}
      <member>
        <IsDefault>{{ "true" if rule.is_default else "false" }}</IsDefault>
        <Conditions>
          {% for condition in rule.conditions %}
          <member>
            <Field>{{ condition["field"] }}</Field>
            <Values>
              {% for value in condition["values"] %}
              <member>{{ value }}</member>
              {% endfor %}
            </Values>
          </member>
          {% endfor %}
        </Conditions>
        <Priority>{{ rule.priority }}</Priority>
        <Actions>
          {% for action in rule.actions %}
          <member>
            <Type>{{ action["type"] }}</Type>
            <TargetGroupArn>{{ action["target_group_arn"] }}</TargetGroupArn>
          </member>
          {% endfor %}
        </Actions>
        <RuleArn>{{ rule.arn }}</RuleArn>
      </member>
      {% endfor %}
    </Rules>
  </SetRulePrioritiesResult>
  <ResponseMetadata>
    <RequestId>4d7a8036-f3a7-11e5-9c02-8fd20490d5a6</RequestId>
  </ResponseMetadata>
</SetRulePrioritiesResponse>"""
