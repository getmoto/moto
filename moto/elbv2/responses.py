from __future__ import unicode_literals
from moto.core.exceptions import RESTError
from moto.core.utils import amzn_request_id
from moto.core.responses import BaseResponse
from .models import elbv2_backends
from .exceptions import DuplicateTagKeysError
from .exceptions import LoadBalancerNotFoundError
from .exceptions import TargetGroupNotFoundError
from .exceptions import ListenerNotFoundError
from .exceptions import ListenerOrBalancerMissingError

SSL_POLICIES = [
    {
        "name": "ELBSecurityPolicy-2016-08",
        "ssl_protocols": ["TLSv1", "TLSv1.1", "TLSv1.2"],
        "ciphers": [
            {"name": "ECDHE-ECDSA-AES128-GCM-SHA256", "priority": 1},
            {"name": "ECDHE-RSA-AES128-GCM-SHA256", "priority": 2},
            {"name": "ECDHE-ECDSA-AES128-SHA256", "priority": 3},
            {"name": "ECDHE-RSA-AES128-SHA256", "priority": 4},
            {"name": "ECDHE-ECDSA-AES128-SHA", "priority": 5},
            {"name": "ECDHE-RSA-AES128-SHA", "priority": 6},
            {"name": "ECDHE-ECDSA-AES256-GCM-SHA384", "priority": 7},
            {"name": "ECDHE-RSA-AES256-GCM-SHA384", "priority": 8},
            {"name": "ECDHE-ECDSA-AES256-SHA384", "priority": 9},
            {"name": "ECDHE-RSA-AES256-SHA384", "priority": 10},
            {"name": "ECDHE-RSA-AES256-SHA", "priority": 11},
            {"name": "ECDHE-ECDSA-AES256-SHA", "priority": 12},
            {"name": "AES128-GCM-SHA256", "priority": 13},
            {"name": "AES128-SHA256", "priority": 14},
            {"name": "AES128-SHA", "priority": 15},
            {"name": "AES256-GCM-SHA384", "priority": 16},
            {"name": "AES256-SHA256", "priority": 17},
            {"name": "AES256-SHA", "priority": 18},
        ],
    },
    {
        "name": "ELBSecurityPolicy-TLS-1-2-2017-01",
        "ssl_protocols": ["TLSv1.2"],
        "ciphers": [
            {"name": "ECDHE-ECDSA-AES128-GCM-SHA256", "priority": 1},
            {"name": "ECDHE-RSA-AES128-GCM-SHA256", "priority": 2},
            {"name": "ECDHE-ECDSA-AES128-SHA256", "priority": 3},
            {"name": "ECDHE-RSA-AES128-SHA256", "priority": 4},
            {"name": "ECDHE-ECDSA-AES256-GCM-SHA384", "priority": 5},
            {"name": "ECDHE-RSA-AES256-GCM-SHA384", "priority": 6},
            {"name": "ECDHE-ECDSA-AES256-SHA384", "priority": 7},
            {"name": "ECDHE-RSA-AES256-SHA384", "priority": 8},
            {"name": "AES128-GCM-SHA256", "priority": 9},
            {"name": "AES128-SHA256", "priority": 10},
            {"name": "AES256-GCM-SHA384", "priority": 11},
            {"name": "AES256-SHA256", "priority": 12},
        ],
    },
    {
        "name": "ELBSecurityPolicy-TLS-1-1-2017-01",
        "ssl_protocols": ["TLSv1.1", "TLSv1.2"],
        "ciphers": [
            {"name": "ECDHE-ECDSA-AES128-GCM-SHA256", "priority": 1},
            {"name": "ECDHE-RSA-AES128-GCM-SHA256", "priority": 2},
            {"name": "ECDHE-ECDSA-AES128-SHA256", "priority": 3},
            {"name": "ECDHE-RSA-AES128-SHA256", "priority": 4},
            {"name": "ECDHE-ECDSA-AES128-SHA", "priority": 5},
            {"name": "ECDHE-RSA-AES128-SHA", "priority": 6},
            {"name": "ECDHE-ECDSA-AES256-GCM-SHA384", "priority": 7},
            {"name": "ECDHE-RSA-AES256-GCM-SHA384", "priority": 8},
            {"name": "ECDHE-ECDSA-AES256-SHA384", "priority": 9},
            {"name": "ECDHE-RSA-AES256-SHA384", "priority": 10},
            {"name": "ECDHE-RSA-AES256-SHA", "priority": 11},
            {"name": "ECDHE-ECDSA-AES256-SHA", "priority": 12},
            {"name": "AES128-GCM-SHA256", "priority": 13},
            {"name": "AES128-SHA256", "priority": 14},
            {"name": "AES128-SHA", "priority": 15},
            {"name": "AES256-GCM-SHA384", "priority": 16},
            {"name": "AES256-SHA256", "priority": 17},
            {"name": "AES256-SHA", "priority": 18},
        ],
    },
    {
        "name": "ELBSecurityPolicy-2015-05",
        "ssl_protocols": ["TLSv1", "TLSv1.1", "TLSv1.2"],
        "ciphers": [
            {"name": "ECDHE-ECDSA-AES128-GCM-SHA256", "priority": 1},
            {"name": "ECDHE-RSA-AES128-GCM-SHA256", "priority": 2},
            {"name": "ECDHE-ECDSA-AES128-SHA256", "priority": 3},
            {"name": "ECDHE-RSA-AES128-SHA256", "priority": 4},
            {"name": "ECDHE-ECDSA-AES128-SHA", "priority": 5},
            {"name": "ECDHE-RSA-AES128-SHA", "priority": 6},
            {"name": "ECDHE-ECDSA-AES256-GCM-SHA384", "priority": 7},
            {"name": "ECDHE-RSA-AES256-GCM-SHA384", "priority": 8},
            {"name": "ECDHE-ECDSA-AES256-SHA384", "priority": 9},
            {"name": "ECDHE-RSA-AES256-SHA384", "priority": 10},
            {"name": "ECDHE-RSA-AES256-SHA", "priority": 11},
            {"name": "ECDHE-ECDSA-AES256-SHA", "priority": 12},
            {"name": "AES128-GCM-SHA256", "priority": 13},
            {"name": "AES128-SHA256", "priority": 14},
            {"name": "AES128-SHA", "priority": 15},
            {"name": "AES256-GCM-SHA384", "priority": 16},
            {"name": "AES256-SHA256", "priority": 17},
            {"name": "AES256-SHA", "priority": 18},
        ],
    },
    {
        "name": "ELBSecurityPolicy-TLS-1-0-2015-04",
        "ssl_protocols": ["TLSv1", "TLSv1.1", "TLSv1.2"],
        "ciphers": [
            {"name": "ECDHE-ECDSA-AES128-GCM-SHA256", "priority": 1},
            {"name": "ECDHE-RSA-AES128-GCM-SHA256", "priority": 2},
            {"name": "ECDHE-ECDSA-AES128-SHA256", "priority": 3},
            {"name": "ECDHE-RSA-AES128-SHA256", "priority": 4},
            {"name": "ECDHE-ECDSA-AES128-SHA", "priority": 5},
            {"name": "ECDHE-RSA-AES128-SHA", "priority": 6},
            {"name": "ECDHE-ECDSA-AES256-GCM-SHA384", "priority": 7},
            {"name": "ECDHE-RSA-AES256-GCM-SHA384", "priority": 8},
            {"name": "ECDHE-ECDSA-AES256-SHA384", "priority": 9},
            {"name": "ECDHE-RSA-AES256-SHA384", "priority": 10},
            {"name": "ECDHE-RSA-AES256-SHA", "priority": 11},
            {"name": "ECDHE-ECDSA-AES256-SHA", "priority": 12},
            {"name": "AES128-GCM-SHA256", "priority": 13},
            {"name": "AES128-SHA256", "priority": 14},
            {"name": "AES128-SHA", "priority": 15},
            {"name": "AES256-GCM-SHA384", "priority": 16},
            {"name": "AES256-SHA256", "priority": 17},
            {"name": "AES256-SHA", "priority": 18},
            {"name": "DES-CBC3-SHA", "priority": 19},
        ],
    },
]


class ELBV2Response(BaseResponse):
    @property
    def elbv2_backend(self):
        return elbv2_backends[self.region]

    @amzn_request_id
    def create_load_balancer(self):
        load_balancer_name = self._get_param("Name")
        subnet_ids = self._get_multi_param("Subnets.member")
        security_groups = self._get_multi_param("SecurityGroups.member")
        scheme = self._get_param("Scheme")
        loadbalancer_type = self._get_param("Type")

        load_balancer = self.elbv2_backend.create_load_balancer(
            name=load_balancer_name,
            security_groups=security_groups,
            subnet_ids=subnet_ids,
            scheme=scheme,
            loadbalancer_type=loadbalancer_type,
        )
        self._add_tags(load_balancer)
        template = self.response_template(CREATE_LOAD_BALANCER_TEMPLATE)
        return template.render(load_balancer=load_balancer)

    @amzn_request_id
    def create_rule(self):
        params = self._get_params()
        actions = self._get_list_prefix("Actions.member")
        rules = self.elbv2_backend.create_rule(
            listener_arn=params["ListenerArn"],
            conditions=params["Conditions"],
            priority=params["Priority"],
            actions=actions,
        )
        template = self.response_template(CREATE_RULE_TEMPLATE)
        return template.render(rules=rules)

    @amzn_request_id
    def create_target_group(self):
        name = self._get_param("Name")
        vpc_id = self._get_param("VpcId")
        protocol = self._get_param("Protocol")
        port = self._get_param("Port")
        healthcheck_protocol = self._get_param("HealthCheckProtocol")
        healthcheck_port = self._get_param("HealthCheckPort")
        healthcheck_path = self._get_param("HealthCheckPath")
        healthcheck_interval_seconds = self._get_param("HealthCheckIntervalSeconds")
        healthcheck_timeout_seconds = self._get_param("HealthCheckTimeoutSeconds")
        healthcheck_enabled = self._get_param("HealthCheckEnabled")
        healthy_threshold_count = self._get_param("HealthyThresholdCount")
        unhealthy_threshold_count = self._get_param("UnhealthyThresholdCount")
        matcher = self._get_param("Matcher")
        target_type = self._get_param("TargetType")

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
            healthcheck_enabled=healthcheck_enabled,
            healthy_threshold_count=healthy_threshold_count,
            unhealthy_threshold_count=unhealthy_threshold_count,
            matcher=matcher,
            target_type=target_type,
        )

        template = self.response_template(CREATE_TARGET_GROUP_TEMPLATE)
        return template.render(target_group=target_group)

    @amzn_request_id
    def create_listener(self):
        load_balancer_arn = self._get_param("LoadBalancerArn")
        protocol = self._get_param("Protocol")
        port = self._get_param("Port")
        ssl_policy = self._get_param("SslPolicy", "ELBSecurityPolicy-2016-08")
        certificates = self._get_list_prefix("Certificates.member")
        if certificates:
            certificate = certificates[0].get("certificate_arn")
        else:
            certificate = None
        default_actions = self._get_list_prefix("DefaultActions.member")

        listener = self.elbv2_backend.create_listener(
            load_balancer_arn=load_balancer_arn,
            protocol=protocol,
            port=port,
            ssl_policy=ssl_policy,
            certificate=certificate,
            default_actions=default_actions,
        )

        template = self.response_template(CREATE_LISTENER_TEMPLATE)
        return template.render(listener=listener)

    @amzn_request_id
    def describe_load_balancers(self):
        arns = self._get_multi_param("LoadBalancerArns.member")
        names = self._get_multi_param("Names.member")
        all_load_balancers = list(
            self.elbv2_backend.describe_load_balancers(arns, names)
        )
        marker = self._get_param("Marker")
        all_names = [balancer.name for balancer in all_load_balancers]
        if marker:
            start = all_names.index(marker) + 1
        else:
            start = 0
        page_size = self._get_int_param(
            "PageSize", 50
        )  # the default is 400, but using 50 to make testing easier
        load_balancers_resp = all_load_balancers[start : start + page_size]
        next_marker = None
        if len(all_load_balancers) > start + page_size:
            next_marker = load_balancers_resp[-1].name

        template = self.response_template(DESCRIBE_LOAD_BALANCERS_TEMPLATE)
        return template.render(load_balancers=load_balancers_resp, marker=next_marker)

    @amzn_request_id
    def describe_rules(self):
        listener_arn = self._get_param("ListenerArn")
        rule_arns = (
            self._get_multi_param("RuleArns.member")
            if any(
                k
                for k in list(self.querystring.keys())
                if k.startswith("RuleArns.member")
            )
            else None
        )
        all_rules = list(self.elbv2_backend.describe_rules(listener_arn, rule_arns))
        all_arns = [rule.arn for rule in all_rules]
        page_size = self._get_int_param("PageSize", 50)  # set 50 for temporary

        marker = self._get_param("Marker")
        if marker:
            start = all_arns.index(marker) + 1
        else:
            start = 0
        rules_resp = all_rules[start : start + page_size]
        next_marker = None

        if len(all_rules) > start + page_size:
            next_marker = rules_resp[-1].arn
        template = self.response_template(DESCRIBE_RULES_TEMPLATE)
        return template.render(rules=rules_resp, marker=next_marker)

    @amzn_request_id
    def describe_target_groups(self):
        load_balancer_arn = self._get_param("LoadBalancerArn")
        target_group_arns = self._get_multi_param("TargetGroupArns.member")
        names = self._get_multi_param("Names.member")

        target_groups = self.elbv2_backend.describe_target_groups(
            load_balancer_arn, target_group_arns, names
        )
        template = self.response_template(DESCRIBE_TARGET_GROUPS_TEMPLATE)
        return template.render(target_groups=target_groups)

    @amzn_request_id
    def describe_target_group_attributes(self):
        target_group_arn = self._get_param("TargetGroupArn")
        target_group = self.elbv2_backend.target_groups.get(target_group_arn)
        if not target_group:
            raise TargetGroupNotFoundError()
        template = self.response_template(DESCRIBE_TARGET_GROUP_ATTRIBUTES_TEMPLATE)
        return template.render(attributes=target_group.attributes)

    @amzn_request_id
    def describe_listeners(self):
        load_balancer_arn = self._get_param("LoadBalancerArn")
        listener_arns = self._get_multi_param("ListenerArns.member")
        if not load_balancer_arn and not listener_arns:
            raise ListenerOrBalancerMissingError()

        listeners = self.elbv2_backend.describe_listeners(
            load_balancer_arn, listener_arns
        )
        template = self.response_template(DESCRIBE_LISTENERS_TEMPLATE)
        return template.render(listeners=listeners)

    @amzn_request_id
    def delete_load_balancer(self):
        arn = self._get_param("LoadBalancerArn")
        self.elbv2_backend.delete_load_balancer(arn)
        template = self.response_template(DELETE_LOAD_BALANCER_TEMPLATE)
        return template.render()

    @amzn_request_id
    def delete_rule(self):
        arn = self._get_param("RuleArn")
        self.elbv2_backend.delete_rule(arn)
        template = self.response_template(DELETE_RULE_TEMPLATE)
        return template.render()

    @amzn_request_id
    def delete_target_group(self):
        arn = self._get_param("TargetGroupArn")
        self.elbv2_backend.delete_target_group(arn)
        template = self.response_template(DELETE_TARGET_GROUP_TEMPLATE)
        return template.render()

    @amzn_request_id
    def delete_listener(self):
        arn = self._get_param("ListenerArn")
        self.elbv2_backend.delete_listener(arn)
        template = self.response_template(DELETE_LISTENER_TEMPLATE)
        return template.render()

    @amzn_request_id
    def modify_rule(self):
        rule_arn = self._get_param("RuleArn")
        params = self._get_params()
        conditions = params["Conditions"]
        actions = self._get_list_prefix("Actions.member")
        rules = self.elbv2_backend.modify_rule(
            rule_arn=rule_arn, conditions=conditions, actions=actions
        )
        template = self.response_template(MODIFY_RULE_TEMPLATE)
        return template.render(rules=rules)

    @amzn_request_id
    def modify_target_group_attributes(self):
        target_group_arn = self._get_param("TargetGroupArn")
        target_group = self.elbv2_backend.target_groups.get(target_group_arn)
        attributes = {
            attr["key"]: attr["value"]
            for attr in self._get_list_prefix("Attributes.member")
        }
        target_group.attributes.update(attributes)
        if not target_group:
            raise TargetGroupNotFoundError()
        template = self.response_template(MODIFY_TARGET_GROUP_ATTRIBUTES_TEMPLATE)
        return template.render(attributes=attributes)

    @amzn_request_id
    def register_targets(self):
        target_group_arn = self._get_param("TargetGroupArn")
        targets = self._get_list_prefix("Targets.member")
        self.elbv2_backend.register_targets(target_group_arn, targets)

        template = self.response_template(REGISTER_TARGETS_TEMPLATE)
        return template.render()

    @amzn_request_id
    def deregister_targets(self):
        target_group_arn = self._get_param("TargetGroupArn")
        targets = self._get_list_prefix("Targets.member")
        self.elbv2_backend.deregister_targets(target_group_arn, targets)

        template = self.response_template(DEREGISTER_TARGETS_TEMPLATE)
        return template.render()

    @amzn_request_id
    def describe_target_health(self):
        target_group_arn = self._get_param("TargetGroupArn")
        targets = self._get_list_prefix("Targets.member")
        target_health_descriptions = self.elbv2_backend.describe_target_health(
            target_group_arn, targets
        )

        template = self.response_template(DESCRIBE_TARGET_HEALTH_TEMPLATE)
        return template.render(target_health_descriptions=target_health_descriptions)

    @amzn_request_id
    def set_rule_priorities(self):
        rule_priorities = self._get_list_prefix("RulePriorities.member")
        for rule_priority in rule_priorities:
            rule_priority["priority"] = int(rule_priority["priority"])
        rules = self.elbv2_backend.set_rule_priorities(rule_priorities)
        template = self.response_template(SET_RULE_PRIORITIES_TEMPLATE)
        return template.render(rules=rules)

    @amzn_request_id
    def add_tags(self):
        resource_arns = self._get_multi_param("ResourceArns.member")

        for arn in resource_arns:
            if ":targetgroup" in arn:
                resource = self.elbv2_backend.target_groups.get(arn)
                if not resource:
                    raise TargetGroupNotFoundError()
            elif ":loadbalancer" in arn:
                resource = self.elbv2_backend.load_balancers.get(arn)
                if not resource:
                    raise LoadBalancerNotFoundError()
            else:
                raise LoadBalancerNotFoundError()
            self._add_tags(resource)

        template = self.response_template(ADD_TAGS_TEMPLATE)
        return template.render()

    @amzn_request_id
    def remove_tags(self):
        resource_arns = self._get_multi_param("ResourceArns.member")
        tag_keys = self._get_multi_param("TagKeys.member")

        for arn in resource_arns:
            if ":targetgroup" in arn:
                resource = self.elbv2_backend.target_groups.get(arn)
                if not resource:
                    raise TargetGroupNotFoundError()
            elif ":loadbalancer" in arn:
                resource = self.elbv2_backend.load_balancers.get(arn)
                if not resource:
                    raise LoadBalancerNotFoundError()
            else:
                raise LoadBalancerNotFoundError()
            [resource.remove_tag(key) for key in tag_keys]

        template = self.response_template(REMOVE_TAGS_TEMPLATE)
        return template.render()

    @amzn_request_id
    def describe_tags(self):
        resource_arns = self._get_multi_param("ResourceArns.member")
        resources = []
        for arn in resource_arns:
            if ":targetgroup" in arn:
                resource = self.elbv2_backend.target_groups.get(arn)
                if not resource:
                    raise TargetGroupNotFoundError()
            elif ":loadbalancer" in arn:
                resource = self.elbv2_backend.load_balancers.get(arn)
                if not resource:
                    raise LoadBalancerNotFoundError()
            elif ":listener" in arn:
                lb_arn, _, _ = arn.replace(":listener", ":loadbalancer").rpartition("/")
                balancer = self.elbv2_backend.load_balancers.get(lb_arn)
                if not balancer:
                    raise LoadBalancerNotFoundError()
                resource = balancer.listeners.get(arn)
                if not resource:
                    raise ListenerNotFoundError()
            else:
                raise LoadBalancerNotFoundError()
            resources.append(resource)

        template = self.response_template(DESCRIBE_TAGS_TEMPLATE)
        return template.render(resources=resources)

    @amzn_request_id
    def describe_account_limits(self):
        # Supports paging but not worth implementing yet
        # marker = self._get_param('Marker')
        # page_size = self._get_int_param('PageSize')

        limits = {
            "application-load-balancers": 20,
            "target-groups": 3000,
            "targets-per-application-load-balancer": 30,
            "listeners-per-application-load-balancer": 50,
            "rules-per-application-load-balancer": 100,
            "network-load-balancers": 20,
            "targets-per-network-load-balancer": 200,
            "listeners-per-network-load-balancer": 50,
        }

        template = self.response_template(DESCRIBE_LIMITS_TEMPLATE)
        return template.render(limits=limits)

    @amzn_request_id
    def describe_ssl_policies(self):
        names = self._get_multi_param("Names.member.")
        # Supports paging but not worth implementing yet
        # marker = self._get_param('Marker')
        # page_size = self._get_int_param('PageSize')

        policies = SSL_POLICIES
        if names:
            policies = filter(lambda policy: policy["name"] in names, policies)

        template = self.response_template(DESCRIBE_SSL_POLICIES_TEMPLATE)
        return template.render(policies=policies)

    @amzn_request_id
    def set_ip_address_type(self):
        arn = self._get_param("LoadBalancerArn")
        ip_type = self._get_param("IpAddressType")

        self.elbv2_backend.set_ip_address_type(arn, ip_type)

        template = self.response_template(SET_IP_ADDRESS_TYPE_TEMPLATE)
        return template.render(ip_type=ip_type)

    @amzn_request_id
    def set_security_groups(self):
        arn = self._get_param("LoadBalancerArn")
        sec_groups = self._get_multi_param("SecurityGroups.member.")

        self.elbv2_backend.set_security_groups(arn, sec_groups)

        template = self.response_template(SET_SECURITY_GROUPS_TEMPLATE)
        return template.render(sec_groups=sec_groups)

    @amzn_request_id
    def set_subnets(self):
        arn = self._get_param("LoadBalancerArn")
        subnets = self._get_multi_param("Subnets.member.")

        subnet_zone_list = self.elbv2_backend.set_subnets(arn, subnets)

        template = self.response_template(SET_SUBNETS_TEMPLATE)
        return template.render(subnets=subnet_zone_list)

    @amzn_request_id
    def modify_load_balancer_attributes(self):
        arn = self._get_param("LoadBalancerArn")
        attrs = self._get_map_prefix(
            "Attributes.member", key_end="Key", value_end="Value"
        )

        all_attrs = self.elbv2_backend.modify_load_balancer_attributes(arn, attrs)

        template = self.response_template(MODIFY_LOADBALANCER_ATTRS_TEMPLATE)
        return template.render(attrs=all_attrs)

    @amzn_request_id
    def describe_load_balancer_attributes(self):
        arn = self._get_param("LoadBalancerArn")
        attrs = self.elbv2_backend.describe_load_balancer_attributes(arn)

        template = self.response_template(DESCRIBE_LOADBALANCER_ATTRS_TEMPLATE)
        return template.render(attrs=attrs)

    @amzn_request_id
    def modify_target_group(self):
        arn = self._get_param("TargetGroupArn")

        health_check_proto = self._get_param(
            "HealthCheckProtocol"
        )  # 'HTTP' | 'HTTPS' | 'TCP',
        health_check_port = self._get_param("HealthCheckPort")
        health_check_path = self._get_param("HealthCheckPath")
        health_check_interval = self._get_param("HealthCheckIntervalSeconds")
        health_check_timeout = self._get_param("HealthCheckTimeoutSeconds")
        health_check_enabled = self._get_param("HealthCheckEnabled")
        healthy_threshold_count = self._get_param("HealthyThresholdCount")
        unhealthy_threshold_count = self._get_param("UnhealthyThresholdCount")
        http_codes = self._get_param("Matcher.HttpCode")

        target_group = self.elbv2_backend.modify_target_group(
            arn,
            health_check_proto,
            health_check_port,
            health_check_path,
            health_check_interval,
            health_check_timeout,
            healthy_threshold_count,
            unhealthy_threshold_count,
            http_codes,
            health_check_enabled=health_check_enabled,
        )

        template = self.response_template(MODIFY_TARGET_GROUP_TEMPLATE)
        return template.render(target_group=target_group)

    @amzn_request_id
    def modify_listener(self):
        arn = self._get_param("ListenerArn")
        port = self._get_param("Port")
        protocol = self._get_param("Protocol")
        ssl_policy = self._get_param("SslPolicy")
        certificates = self._get_list_prefix("Certificates.member")
        default_actions = self._get_list_prefix("DefaultActions.member")

        # Should really move SSL Policies to models
        if ssl_policy is not None and ssl_policy not in [
            item["name"] for item in SSL_POLICIES
        ]:
            raise RESTError(
                "SSLPolicyNotFound", "Policy {0} not found".format(ssl_policy)
            )

        listener = self.elbv2_backend.modify_listener(
            arn, port, protocol, ssl_policy, certificates, default_actions
        )

        template = self.response_template(MODIFY_LISTENER_TEMPLATE)
        return template.render(listener=listener)

    def _add_tags(self, resource):
        tag_values = []
        tag_keys = []

        for t_key, t_val in sorted(self.querystring.items()):
            if t_key.startswith("Tags.member."):
                if t_key.split(".")[3] == "Key":
                    tag_keys.extend(t_val)
                elif t_key.split(".")[3] == "Value":
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
    <RequestId>{{ request_id }}</RequestId>
  </ResponseMetadata>
</AddTagsResponse>"""

REMOVE_TAGS_TEMPLATE = """<RemoveTagsResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2015-12-01/">
  <RemoveTagsResult/>
  <ResponseMetadata>
    <RequestId>{{ request_id }}</RequestId>
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
    <RequestId>{{ request_id }}</RequestId>
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
          <Code>{{ load_balancer.state }}</Code>
        </State>
        <Type>{{ load_balancer.loadbalancer_type }}</Type>
      </member>
    </LoadBalancers>
  </CreateLoadBalancerResult>
  <ResponseMetadata>
    <RequestId>{{ request_id }}</RequestId>
  </ResponseMetadata>
</CreateLoadBalancerResponse>"""

CREATE_RULE_TEMPLATE = """<CreateRuleResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2015-12-01/">
  <CreateRuleResult>
    <Rules>
      <member>
        <IsDefault>{{ "true" if rules.is_default else "false" }}</IsDefault>
        <Conditions>
          {% for condition in rules.conditions %}
          <member>
            <Field>{{ condition["Field"] }}</Field>
            {% if "Values" in condition %}
            <Values>
              {% for value in condition["Values"] %}
              <member>{{ value }}</member>
              {% endfor %}
            </Values>
            {% endif %}
            {% if "HttpHeaderConfig" in condition %}
            <HttpHeaderConfig>
              <HttpHeaderName>{{ condition["HttpHeaderConfig"]["HttpHeaderName"] }}</HttpHeaderName>
              <Values>
                {% for value in condition["HttpHeaderConfig"]["Values"] %}
                <member>{{ value }}</member>
                {% endfor %}
              </Values>
            </HttpHeaderConfig>
            {% endif %}
            {% if "HttpRequestMethodConfig" in condition %}
            <HttpRequestMethodConfig>
              <Values>
                {% for value in condition["HttpRequestMethodConfig"]["Values"] %}
                <member>{{ value }}</member>
                {% endfor %}
              </Values>
            </HttpRequestMethodConfig>
            {% endif %}
            {% if "QueryStringConfig" in condition %}
            <QueryStringConfig>
              <Values>
                {% for value in condition["QueryStringConfig"]["Values"] %}
                <member>
                    <Key>{{ value["Key"] }}</Key>
                    <Value>{{ value["Value"] }}</Value>
                </member>
                {% endfor %}
              </Values>
            </QueryStringConfig>
            {% endif %}
            {% if "SourceIpConfig" in condition %}
            <SourceIpConfig>
              <Values>
                {% for value in condition["SourceIpConfig"]["Values"] %}
                <member>{{ value }}</member>
                {% endfor %}
              </Values>
            </SourceIpConfig>
            {% endif %}
            {% if "PathPatternConfig" in condition %}
            <PathPatternConfig>
              <Values>
                {% for value in condition["PathPatternConfig"]["Values"] %}
                <member>{{ value }}</member>
                {% endfor %}
              </Values>
            </PathPatternConfig>
            {% endif %}
            {% if "HostHeaderConfig" in condition %}
            <HostHeaderConfig>
              <Values>
                {% for value in condition["HostHeaderConfig"]["Values"] %}
                <member>{{ value }}</member>
                {% endfor %}
              </Values>
            </HostHeaderConfig>
            {% endif %}
          </member>
          {% endfor %}
        </Conditions>
        <Priority>{{ rules.priority }}</Priority>
        <RuleArn>{{ rules.arn }}</RuleArn>
        <Actions>
          {% for action in rules.actions %}
          <member>
            <Type>{{ action["type"] }}</Type>
            {% if action["type"] == "forward" and "forward_config" in action.data %}
            <ForwardConfig>
              <TargetGroups>
                {% for target_group in action.data["forward_config"]["target_groups"] %}
                <member>
                  <TargetGroupArn>{{ target_group["target_group_arn"] }}</TargetGroupArn>
                  <Weight>{{ target_group["weight"] }}</Weight>
                </member>
                {% endfor %}
              </TargetGroups>
            </ForwardConfig>
            {% endif %}
            {% if action["type"] == "forward" and "forward_config" not in action.data %}
            <TargetGroupArn>{{ action["target_group_arn"] }}</TargetGroupArn>
            {% elif action["type"] == "redirect" %}
            <RedirectConfig>{{ action["redirect_config"] }}</RedirectConfig>
            {% endif %}
          </member>
          {% endfor %}
        </Actions>
      </member>
    </Rules>
  </CreateRuleResult>
  <ResponseMetadata>
    <RequestId>{{ request_id }}</RequestId>
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
        <HealthCheckPort>{{ target_group.healthcheck_port or '' }}</HealthCheckPort>
        <HealthCheckPath>{{ target_group.healthcheck_path or '' }}</HealthCheckPath>
        <HealthCheckIntervalSeconds>{{ target_group.healthcheck_interval_seconds }}</HealthCheckIntervalSeconds>
        <HealthCheckTimeoutSeconds>{{ target_group.healthcheck_timeout_seconds }}</HealthCheckTimeoutSeconds>
        <HealthCheckEnabled>{{ target_group.healthcheck_enabled and 'true' or 'false' }}</HealthCheckEnabled>
        <HealthyThresholdCount>{{ target_group.healthy_threshold_count }}</HealthyThresholdCount>
        <UnhealthyThresholdCount>{{ target_group.unhealthy_threshold_count }}</UnhealthyThresholdCount>
        {% if target_group.matcher %}
        <Matcher>
          <HttpCode>{{ target_group.matcher['HttpCode'] }}</HttpCode>
        </Matcher>
        {% endif %}
        {% if target_group.target_type %}
        <TargetType>{{ target_group.target_type }}</TargetType>
        {% endif %}
      </member>
    </TargetGroups>
  </CreateTargetGroupResult>
  <ResponseMetadata>
    <RequestId>{{ request_id }}</RequestId>
  </ResponseMetadata>
</CreateTargetGroupResponse>"""

CREATE_LISTENER_TEMPLATE = """<CreateListenerResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2015-12-01/">
  <CreateListenerResult>
    <Listeners>
      <member>
        <LoadBalancerArn>{{ listener.load_balancer_arn }}</LoadBalancerArn>
        <Protocol>{{ listener.protocol }}</Protocol>
        {% if listener.certificates %}
        <Certificates>
          {% for cert in listener.certificates %}
          <member>
            <CertificateArn>{{ cert }}</CertificateArn>
          </member>
          {% endfor %}
        </Certificates>
        {% endif %}
        <Port>{{ listener.port }}</Port>
        <SslPolicy>{{ listener.ssl_policy }}</SslPolicy>
        <ListenerArn>{{ listener.arn }}</ListenerArn>
        <DefaultActions>
          {% for action in listener.default_actions %}
          <member>
            {{ action.to_xml() }}
          </member>
          {% endfor %}
        </DefaultActions>
      </member>
    </Listeners>
  </CreateListenerResult>
  <ResponseMetadata>
    <RequestId>{{ request_id }}</RequestId>
  </ResponseMetadata>
</CreateListenerResponse>"""

DELETE_LOAD_BALANCER_TEMPLATE = """<DeleteLoadBalancerResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2015-12-01/">
  <DeleteLoadBalancerResult/>
  <ResponseMetadata>
    <RequestId>{{ request_id }}</RequestId>
  </ResponseMetadata>
</DeleteLoadBalancerResponse>"""

DELETE_RULE_TEMPLATE = """<DeleteRuleResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2015-12-01/">
  <DeleteRuleResult/>
  <ResponseMetadata>
    <RequestId>{{ request_id }}</RequestId>
  </ResponseMetadata>
</DeleteRuleResponse>"""

DELETE_TARGET_GROUP_TEMPLATE = """<DeleteTargetGroupResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2015-12-01/">
  <DeleteTargetGroupResult/>
  <ResponseMetadata>
    <RequestId>{{ request_id }}</RequestId>
  </ResponseMetadata>
</DeleteTargetGroupResponse>"""

DELETE_LISTENER_TEMPLATE = """<DeleteListenerResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2015-12-01/">
  <DeleteListenerResult/>
  <ResponseMetadata>
    <RequestId>{{ request_id }}</RequestId>
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
          <Code>{{ load_balancer.state }}</Code>
        </State>
        <Type>{{ load_balancer.loadbalancer_type }}</Type>
        <IpAddressType>ipv4</IpAddressType>
      </member>
      {% endfor %}
    </LoadBalancers>
    {% if marker %}
    <NextMarker>{{ marker }}</NextMarker>
    {% endif %}
  </DescribeLoadBalancersResult>
  <ResponseMetadata>
    <RequestId>{{ request_id }}</RequestId>
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
            <Field>{{ condition["Field"] }}</Field>
            {% if "HttpHeaderConfig" in condition %}
            <HttpHeaderConfig>
              <HttpHeaderName>{{ condition["HttpHeaderConfig"]["HttpHeaderName"] }}</HttpHeaderName>
              <Values>
                {% for value in condition["HttpHeaderConfig"]["Values"] %}
                  <member>{{ value }}</member>
                {% endfor %}
              </Values>
            </HttpHeaderConfig>
            {% endif %}
            {% if "HttpRequestMethodConfig" in condition %}
            <HttpRequestMethodConfig>
              <Values>
                {% for value in condition["HttpRequestMethodConfig"]["Values"] %}
                <member>{{ value }}</member>
                {% endfor %}
              </Values>
            </HttpRequestMethodConfig>
            {% endif %}
            {% if "QueryStringConfig" in condition %}
            <QueryStringConfig>
              <Values>
                {% for value in condition["QueryStringConfig"]["Values"] %}
                <member>
                    <Key>{{ value["Key"] }}</Key>
                    <Value>{{ value["Value"] }}</Value>
                </member>
                {% endfor %}
              </Values>
            </QueryStringConfig>
            {% endif %}
            {% if "SourceIpConfig" in condition %}
            <SourceIpConfig>
              <Values>
                {% for value in condition["SourceIpConfig"]["Values"] %}
                <member>{{ value }}</member>
                {% endfor %}
              </Values>
            </SourceIpConfig>
            {% endif %}
            {% if "PathPatternConfig" in condition %}
            <PathPatternConfig>
              <Values>
                {% for value in condition["PathPatternConfig"]["Values"] %}
                <member>{{ value }}</member>
                {% endfor %}
              </Values>
            </PathPatternConfig>
            {% endif %}
            {% if "HostHeaderConfig" in condition %}
            <HostHeaderConfig>
              <Values>
                {% for value in condition["HostHeaderConfig"]["Values"] %}
                <member>{{ value }}</member>
                {% endfor %}
              </Values>
            </HostHeaderConfig>
            {% endif %}
            {% if "Values" in condition %}
            <Values>
              {% for value in condition["Values"] %}
              <member>{{ value }}</member>
              {% endfor %}
            </Values>
            {% endif %}
          </member>
          {% endfor %}
        </Conditions>
        <Priority>{{ rule.priority }}</Priority>
        <RuleArn>{{ rule.arn }}</RuleArn>
        <Actions>
          {% for action in rule.actions %}
          <member>
            {{ action.to_xml() }}
          </member>
          {% endfor %}
        </Actions>
      </member>
      {% endfor %}
    </Rules>
    {% if marker %}
    <NextMarker>{{ marker }}</NextMarker>
    {% endif %}
  </DescribeRulesResult>
  <ResponseMetadata>
    <RequestId>{{ request_id }}</RequestId>
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
        <HealthCheckProtocol>{{ target_group.healthcheck_protocol }}</HealthCheckProtocol>
        <HealthCheckPort>{{ target_group.healthcheck_port or '' }}</HealthCheckPort>
        <HealthCheckPath>{{ target_group.healthcheck_path or '' }}</HealthCheckPath>
        <HealthCheckIntervalSeconds>{{ target_group.healthcheck_interval_seconds }}</HealthCheckIntervalSeconds>
        <HealthCheckTimeoutSeconds>{{ target_group.healthcheck_timeout_seconds }}</HealthCheckTimeoutSeconds>
        <HealthCheckEnabled>{{ target_group.healthcheck_enabled and 'true' or 'false' }}</HealthCheckEnabled>
        <HealthyThresholdCount>{{ target_group.healthy_threshold_count }}</HealthyThresholdCount>
        <UnhealthyThresholdCount>{{ target_group.unhealthy_threshold_count }}</UnhealthyThresholdCount>
        {% if target_group.matcher %}
        <Matcher>
          <HttpCode>{{ target_group.matcher['HttpCode'] }}</HttpCode>
        </Matcher>
        {% endif %}
        {% if target_group.target_type %}
        <TargetType>{{ target_group.target_type }}</TargetType>
        {% endif %}
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
    <RequestId>{{ request_id }}</RequestId>
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
    <RequestId>{{ request_id }}</RequestId>
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
            {{ action.to_xml() }}
          </member>
          {% endfor %}
        </DefaultActions>
      </member>
      {% endfor %}
    </Listeners>
  </DescribeListenersResult>
  <ResponseMetadata>
    <RequestId>{{ request_id }}</RequestId>
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
    <RequestId>{{ request_id }}</RequestId>
  </ResponseMetadata>
</ConfigureHealthCheckResponse>"""

MODIFY_RULE_TEMPLATE = """<ModifyRuleResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2015-12-01/">
  <ModifyRuleResult>
    <Rules>
      <member>
        <IsDefault>{{ "true" if rules.is_default else "false" }}</IsDefault>
        <Conditions>
          {% for condition in rules.conditions %}
          <member>
            <Field>{{ condition["Field"] }}</Field>
            {% if "PathPatternConfig" in condition %}
            <PathPatternConfig>
              <Values>
                {% for value in condition["PathPatternConfig"]["Values"] %}
                <member>{{ value }}</member>
                {% endfor %}
              </Values>
            </PathPatternConfig>
            {% endif %}
            {% if "HostHeaderConfig" in condition %}
            <HostHeaderConfig>
              <Values>
                {% for value in condition["HostHeaderConfig"]["Values"] %}
                <member>{{ value }}</member>
                {% endfor %}
              </Values>
            </HostHeaderConfig>
            {% endif %}
            {% if "HttpHeaderConfig" in condition %}
            <HttpHeaderConfig>
              <HttpHeaderName>{{ condition["HttpHeaderConfig"]["HttpHeaderName"] }}</HttpHeaderName>
              <Values>
                {% for value in condition["HttpHeaderConfig"]["Values"] %}
                <member>{{ value }}</member>
                {% endfor %}
              </Values>
            </HttpHeaderConfig>
            {% endif %}
            {% if "HttpRequestMethodConfig" in condition %}
            <HttpRequestMethodConfig>
              <Values>
                {% for value in condition["HttpRequestMethodConfig"]["Values"] %}
                <member>{{ value }}</member>
                {% endfor %}
              </Values>
            </HttpRequestMethodConfig>
            {% endif %}
            {% if "QueryStringConfig" in condition %}
            <QueryStringConfig>
              <Values>
                {% for value in condition["QueryStringConfig"]["Values"] %}
                <member>
                    <Key>{{ value["Key"] }}</Key>
                    <Value>{{ value["Value"] }}</Value>
                </member>
                {% endfor %}
              </Values>
            </QueryStringConfig>
            {% endif %}
            {% if "SourceIpConfig" in condition %}
            <SourceIpConfig>
              <Values>
                {% for value in condition["SourceIpConfig"]["Values"] %}
                <member>{{ value }}</member>
                {% endfor %}
              </Values>
            </SourceIpConfig>
            {% endif %}
            {% if "Values" in condition %}
            <Values>
              {% for value in condition["Values"] %}
              <member>{{ value }}</member>
              {% endfor %}
            </Values>
            {% endif %}
          </member>
          {% endfor %}
        </Conditions>
        <Priority>{{ rules.priority }}</Priority>
        <RuleArn>{{ rules.arn }}</RuleArn>
        <Actions>
          {% for action in rules.actions %}
          <member>
            {{ action.to_xml() }}
          </member>
          {% endfor %}
        </Actions>
      </member>
    </Rules>
  </ModifyRuleResult>
  <ResponseMetadata>
    <RequestId>{{ request_id }}</RequestId>
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
    <RequestId>{{ request_id }}</RequestId>
  </ResponseMetadata>
</ModifyTargetGroupAttributesResponse>"""

REGISTER_TARGETS_TEMPLATE = """<RegisterTargetsResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2015-12-01/">
  <RegisterTargetsResult>
  </RegisterTargetsResult>
  <ResponseMetadata>
    <RequestId>{{ request_id }}</RequestId>
  </ResponseMetadata>
</RegisterTargetsResponse>"""

DEREGISTER_TARGETS_TEMPLATE = """<DeregisterTargetsResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2015-12-01/">
  <DeregisterTargetsResult>
  </DeregisterTargetsResult>
  <ResponseMetadata>
    <RequestId>{{ request_id }}</RequestId>
  </ResponseMetadata>
</DeregisterTargetsResponse>"""

SET_LOAD_BALANCER_SSL_CERTIFICATE = """<SetLoadBalancerListenerSSLCertificateResponse xmlns="http://elasticloadbalan cing.amazonaws.com/doc/2015-12-01/">
 <SetLoadBalancerListenerSSLCertificateResult/>
<ResponseMetadata>
    <RequestId>{{ request_id }}</RequestId>
</ResponseMetadata>
</SetLoadBalancerListenerSSLCertificateResponse>"""

DELETE_LOAD_BALANCER_LISTENERS = """<DeleteLoadBalancerListenersResponse xmlns="http://elasticloadbalan cing.amazonaws.com/doc/2015-12-01/">
 <DeleteLoadBalancerListenersResult/>
<ResponseMetadata>
    <RequestId>{{ request_id }}</RequestId>
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
    <RequestId>{{ request_id }}</RequestId>
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
    <RequestId>{{ request_id }}</RequestId>
  </ResponseMetadata>
</ModifyLoadBalancerAttributesResponse>
"""

CREATE_LOAD_BALANCER_POLICY_TEMPLATE = """<CreateLoadBalancerPolicyResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2015-12-01/">
  <CreateLoadBalancerPolicyResult/>
  <ResponseMetadata>
      <RequestId>{{ request_id }}</RequestId>
  </ResponseMetadata>
</CreateLoadBalancerPolicyResponse>
"""

SET_LOAD_BALANCER_POLICIES_OF_LISTENER_TEMPLATE = """<SetLoadBalancerPoliciesOfListenerResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2015-12-01/">
    <SetLoadBalancerPoliciesOfListenerResult/>
    <ResponseMetadata>
        <RequestId>{{ request_id }}</RequestId>
    </ResponseMetadata>
</SetLoadBalancerPoliciesOfListenerResponse>
"""

SET_LOAD_BALANCER_POLICIES_FOR_BACKEND_SERVER_TEMPLATE = """<SetLoadBalancerPoliciesForBackendServerResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2015-12-01/">
    <SetLoadBalancerPoliciesForBackendServerResult/>
    <ResponseMetadata>
        <RequestId>{{ request_id }}</RequestId>
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
          {% if target_health.reason %}
            <Reason>{{ target_health.reason }}</Reason>
          {% endif %}
          {% if target_health.description %}
            <Description>{{ target_health.description }}</Description>
          {% endif %}
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
    <RequestId>{{ request_id }}</RequestId>
  </ResponseMetadata>
</DescribeTargetHealthResponse>"""

SET_RULE_PRIORITIES_TEMPLATE = """<SetRulePrioritiesResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2015-12-01/">
  <SetRulePrioritiesResult>
    <Rules>
      <member>
        <IsDefault>{{ "true" if rules.is_default else "false" }}</IsDefault>
        <Conditions>
          {% for condition in rules.conditions %}
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
        <Priority>{{ rules.priority }}</Priority>
        <RuleArn>{{ rules.arn }}</RuleArn>
        <Actions>
          {% for action in rules.actions %}
          <member>
            <Type>{{ action["type"] }}</Type>
            {% if action["type"] == "forward" and "forward_config" in action.data %}
            <ForwardConfig>
              <TargetGroups>
                {% for target_group in action.data["forward_config"]["target_groups"] %}
                <member>
                  <TargetGroupArn>{{ target_group["target_group_arn"] }}</TargetGroupArn>
                  <Weight>{{ target_group["weight"] }}</Weight>
                </member>
                {% endfor %}
              </TargetGroups>
            </ForwardConfig>
            {% endif %}
            {% if action["type"] == "forward" and "forward_config" not in action.data %}
            <TargetGroupArn>{{ action["target_group_arn"] }}</TargetGroupArn>
            {% endif %}
          </member>
          {% endfor %}
        </Actions>
      </member>
    </Rules>
  </SetRulePrioritiesResult>
  <ResponseMetadata>
    <RequestId>{{ request_id }}</RequestId>
  </ResponseMetadata>
</SetRulePrioritiesResponse>"""

DESCRIBE_LIMITS_TEMPLATE = """<DescribeAccountLimitsResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2015-12-01/">
  <DescribeAccountLimitsResult>
    <Limits>
      {% for key, value in limits.items() %}
      <member>
        <Name>{{ key }}</Name>
        <Max>{{ value }}</Max>
      </member>
      {% endfor %}
    </Limits>
  </DescribeAccountLimitsResult>
  <ResponseMetadata>
    <RequestId>{{ request_id }}</RequestId>
  </ResponseMetadata>
</DescribeAccountLimitsResponse>"""

DESCRIBE_SSL_POLICIES_TEMPLATE = """<DescribeSSLPoliciesResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2015-12-01/">
  <DescribeSSLPoliciesResult>
    <SslPolicies>
      {% for policy in policies %}
      <member>
        <Name>{{ policy['name'] }}</Name>
        <Ciphers>
          {% for cipher in policy['ciphers'] %}
          <member>
            <Name>{{ cipher['name'] }}</Name>
            <Priority>{{ cipher['priority'] }}</Priority>
          </member>
          {% endfor %}
        </Ciphers>
        <SslProtocols>
          {% for proto in policy['ssl_protocols'] %}
          <member>{{ proto }}</member>
          {% endfor %}
        </SslProtocols>
      </member>
      {% endfor %}
    </SslPolicies>
  </DescribeSSLPoliciesResult>
  <ResponseMetadata>
    <RequestId>{{ request_id }}</RequestId>
  </ResponseMetadata>
</DescribeSSLPoliciesResponse>"""

SET_IP_ADDRESS_TYPE_TEMPLATE = """<SetIpAddressTypeResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2015-12-01/">
  <SetIpAddressTypeResult>
    <IpAddressType>{{ ip_type }}</IpAddressType>
  </SetIpAddressTypeResult>
  <ResponseMetadata>
    <RequestId>{{ request_id }}</RequestId>
  </ResponseMetadata>
</SetIpAddressTypeResponse>"""

SET_SECURITY_GROUPS_TEMPLATE = """<SetSecurityGroupsResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2015-12-01/">
  <SetSecurityGroupsResult>
    <SecurityGroupIds>
      {% for group in sec_groups %}
      <member>{{ group }}</member>
      {% endfor %}
    </SecurityGroupIds>
  </SetSecurityGroupsResult>
  <ResponseMetadata>
    <RequestId>{{ request_id }}</RequestId>
  </ResponseMetadata>
</SetSecurityGroupsResponse>"""

SET_SUBNETS_TEMPLATE = """<SetSubnetsResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2015-12-01/">
  <SetSubnetsResult>
    <AvailabilityZones>
      {% for zone_id, subnet_id in subnets %}
      <member>
        <SubnetId>{{ subnet_id }}</SubnetId>
        <ZoneName>{{ zone_id }}</ZoneName>
      </member>
      {% endfor %}
    </AvailabilityZones>
  </SetSubnetsResult>
  <ResponseMetadata>
    <RequestId>{{ request_id }}</RequestId>
  </ResponseMetadata>
</SetSubnetsResponse>"""

MODIFY_LOADBALANCER_ATTRS_TEMPLATE = """<ModifyLoadBalancerAttributesResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2015-12-01/">
  <ModifyLoadBalancerAttributesResult>
    <Attributes>
      {% for key, value in attrs.items() %}
      <member>
        {% if value == None %}<Value />{% else %}<Value>{{ value }}</Value>{% endif %}
        <Key>{{ key }}</Key>
      </member>
      {% endfor %}
    </Attributes>
  </ModifyLoadBalancerAttributesResult>
  <ResponseMetadata>
    <RequestId>{{ request_id }}</RequestId>
  </ResponseMetadata>
</ModifyLoadBalancerAttributesResponse>"""

DESCRIBE_LOADBALANCER_ATTRS_TEMPLATE = """<DescribeLoadBalancerAttributesResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2015-12-01/">
  <DescribeLoadBalancerAttributesResult>
    <Attributes>
      {% for key, value in attrs.items() %}
      <member>
        {% if value == None %}<Value />{% else %}<Value>{{ value }}</Value>{% endif %}
        <Key>{{ key }}</Key>
      </member>
      {% endfor %}
    </Attributes>
  </DescribeLoadBalancerAttributesResult>
  <ResponseMetadata>
    <RequestId>{{ request_id }}</RequestId>
  </ResponseMetadata>
</DescribeLoadBalancerAttributesResponse>"""

MODIFY_TARGET_GROUP_TEMPLATE = """<ModifyTargetGroupResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2015-12-01/">
  <ModifyTargetGroupResult>
    <TargetGroups>
      <member>
        <TargetGroupArn>{{ target_group.arn }}</TargetGroupArn>
        <TargetGroupName>{{ target_group.name }}</TargetGroupName>
        <Protocol>{{ target_group.protocol }}</Protocol>
        <Port>{{ target_group.port }}</Port>
        <VpcId>{{ target_group.vpc_id }}</VpcId>
        <HealthCheckProtocol>{{ target_group.healthcheck_protocol }}</HealthCheckProtocol>
        <HealthCheckPort>{{ target_group.healthcheck_port }}</HealthCheckPort>
        <HealthCheckPath>{{ target_group.healthcheck_path }}</HealthCheckPath>
        <HealthCheckIntervalSeconds>{{ target_group.healthcheck_interval_seconds }}</HealthCheckIntervalSeconds>
        <HealthCheckTimeoutSeconds>{{ target_group.healthcheck_timeout_seconds }}</HealthCheckTimeoutSeconds>
        <HealthyThresholdCount>{{ target_group.healthy_threshold_count }}</HealthyThresholdCount>
        <UnhealthyThresholdCount>{{ target_group.unhealthy_threshold_count }}</UnhealthyThresholdCount>
        <Matcher>
          <HttpCode>{{ target_group.matcher['HttpCode'] }}</HttpCode>
        </Matcher>
        <LoadBalancerArns>
          {% for load_balancer_arn in target_group.load_balancer_arns %}
          <member>{{ load_balancer_arn }}</member>
          {% endfor %}
        </LoadBalancerArns>
      </member>
    </TargetGroups>
  </ModifyTargetGroupResult>
  <ResponseMetadata>
    <RequestId>{{ request_id }}</RequestId>
  </ResponseMetadata>
</ModifyTargetGroupResponse>"""

MODIFY_LISTENER_TEMPLATE = """<ModifyListenerResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2015-12-01/">
  <ModifyListenerResult>
    <Listeners>
      <member>
        <LoadBalancerArn>{{ listener.load_balancer_arn }}</LoadBalancerArn>
        <Protocol>{{ listener.protocol }}</Protocol>
        {% if listener.certificates %}
        <Certificates>
          {% for cert in listener.certificates %}
          <member>
            <CertificateArn>{{ cert }}</CertificateArn>
          </member>
          {% endfor %}
        </Certificates>
        {% endif %}
        <Port>{{ listener.port }}</Port>
        <SslPolicy>{{ listener.ssl_policy }}</SslPolicy>
        <ListenerArn>{{ listener.arn }}</ListenerArn>
        <DefaultActions>
          {% for action in listener.default_actions %}
          <member>
            {{ action.to_xml() }}
          </member>
          {% endfor %}
        </DefaultActions>
      </member>
    </Listeners>
  </ModifyListenerResult>
  <ResponseMetadata>
    <RequestId>{{ request_id }}</RequestId>
  </ResponseMetadata>
</ModifyListenerResponse>"""
