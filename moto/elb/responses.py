from collections import defaultdict
from typing import Any

from moto.core.responses import ActionResult, BaseResponse, EmptyResult

from .exceptions import DuplicateTagKeysError, LoadBalancerNotFoundError
from .models import ELBBackend, LoadBalancer, elb_backends
from .policies import Policy


def transform_dict(data: dict[str, str]) -> list[dict[str, str]]:
    transformed = [{"Key": key, "Value": value} for key, value in data.items()]
    return transformed


def transform_tuple_list(data: list[tuple[str, str]]) -> list[dict[str, str]]:
    transformed = [{"Key": t[0], "Value": t[1]} for t in data]
    return transformed


def transform_policies(policies: list[Policy]) -> dict[str, Any]:
    segmented_policies = defaultdict(list)
    for policy in policies:
        if policy.policy_type_name in [
            "AppCookieStickinessPolicy",
            "LbCookieStickinessPolicy",
        ]:
            segmented_policies[policy.policy_type_name].append(policy)
        else:
            segmented_policies["OtherPolicy"].append(policy)
    transformed = {
        "AppCookieStickinessPolicies": segmented_policies["AppCookieStickinessPolicy"],
        "LBCookieStickinessPolicies": segmented_policies["LbCookieStickinessPolicy"],
        "OtherPolicies": [p.policy_name for p in segmented_policies["OtherPolicy"]],
    }
    return transformed


class ELBResponse(BaseResponse):
    RESPONSE_KEY_PATH_TO_TRANSFORMER = {
        "DescribeAccessPointsOutput.LoadBalancerDescriptions.LoadBalancerDescription.Policies": transform_policies,
        "DescribeLoadBalancerAttributesOutput.LoadBalancerAttributes.AdditionalAttributes": transform_tuple_list,
        "DescribeTagsOutput.TagDescriptions.TagDescription.Tags": transform_dict,
        "ModifyLoadBalancerAttributesOutput.LoadBalancerAttributes.AdditionalAttributes": transform_tuple_list,
    }

    def __init__(self) -> None:
        super().__init__(service_name="elb")

    @property
    def elb_backend(self) -> ELBBackend:
        return elb_backends[self.current_account][self.region]

    def create_load_balancer(self) -> ActionResult:
        load_balancer_name = self._get_param("LoadBalancerName")
        availability_zones = self._get_multi_param("AvailabilityZones.member")
        ports = self._get_list_prefix("Listeners.member")
        scheme = self._get_param("Scheme")
        subnets = self._get_multi_param("Subnets.member")
        security_groups = self._get_multi_param("SecurityGroups.member")

        load_balancer = self.elb_backend.create_load_balancer(
            name=load_balancer_name,
            zones=availability_zones,
            ports=ports,
            scheme=scheme,
            subnets=subnets,
            security_groups=security_groups,
        )
        self._add_tags(load_balancer)
        result = {"DNSName": load_balancer.dns_name}
        return ActionResult(result)

    def create_load_balancer_listeners(self) -> ActionResult:
        load_balancer_name = self._get_param("LoadBalancerName")
        ports = self._get_list_prefix("Listeners.member")

        self.elb_backend.create_load_balancer_listeners(
            name=load_balancer_name, ports=ports
        )
        return EmptyResult()

    def describe_load_balancers(self) -> ActionResult:
        names = self._get_multi_param("LoadBalancerNames.member")
        all_load_balancers = list(self.elb_backend.describe_load_balancers(names))
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

        result = {
            "LoadBalancerDescriptions": load_balancers_resp,
            "NextMarker": next_marker,
        }
        return ActionResult(result)

    def delete_load_balancer_listeners(self) -> ActionResult:
        load_balancer_name = self._get_param("LoadBalancerName")
        ports = self._get_multi_param("LoadBalancerPorts.member")
        ports = [int(port) for port in ports]

        self.elb_backend.delete_load_balancer_listeners(load_balancer_name, ports)
        return EmptyResult()

    def delete_load_balancer(self) -> ActionResult:
        load_balancer_name = self._get_param("LoadBalancerName")
        self.elb_backend.delete_load_balancer(load_balancer_name)
        return EmptyResult()

    def delete_load_balancer_policy(self) -> ActionResult:
        load_balancer_name = self.querystring.get("LoadBalancerName")[0]  # type: ignore
        names = self._get_param("PolicyName")
        self.elb_backend.delete_load_balancer_policy(
            lb_name=load_balancer_name, policy_name=names
        )
        return EmptyResult()

    def apply_security_groups_to_load_balancer(self) -> ActionResult:
        load_balancer_name = self._get_param("LoadBalancerName")
        security_group_ids = self._get_multi_param("SecurityGroups.member")
        self.elb_backend.apply_security_groups_to_load_balancer(
            load_balancer_name, security_group_ids
        )
        result = {"SecurityGroups": security_group_ids}
        return ActionResult(result)

    def configure_health_check(self) -> ActionResult:
        check = self.elb_backend.configure_health_check(
            load_balancer_name=self._get_param("LoadBalancerName"),
            timeout=self._get_param("HealthCheck.Timeout"),
            healthy_threshold=self._get_param("HealthCheck.HealthyThreshold"),
            unhealthy_threshold=self._get_param("HealthCheck.UnhealthyThreshold"),
            interval=self._get_param("HealthCheck.Interval"),
            target=self._get_param("HealthCheck.Target"),
        )
        result = {"HealthCheck": check}
        return ActionResult(result)

    def register_instances_with_load_balancer(self) -> ActionResult:
        load_balancer_name = self._get_param("LoadBalancerName")
        instance_ids = [
            list(param.values())[0]
            for param in self._get_list_prefix("Instances.member")
        ]
        load_balancer = self.elb_backend.register_instances(
            load_balancer_name, instance_ids
        )
        result = {"Instances": [load_balancer.instance_ids]}
        return ActionResult(result)

    def set_load_balancer_listener_ssl_certificate(self) -> ActionResult:
        load_balancer_name = self._get_param("LoadBalancerName")
        ssl_certificate_id = self.querystring["SSLCertificateId"][0]
        lb_port = self.querystring["LoadBalancerPort"][0]

        self.elb_backend.set_load_balancer_listener_ssl_certificate(
            load_balancer_name, lb_port, ssl_certificate_id
        )
        return EmptyResult()

    def deregister_instances_from_load_balancer(self) -> ActionResult:
        load_balancer_name = self._get_param("LoadBalancerName")
        instance_ids = [
            list(param.values())[0]
            for param in self._get_list_prefix("Instances.member")
        ]
        load_balancer = self.elb_backend.deregister_instances(
            load_balancer_name, instance_ids
        )
        result = {"Instances": [load_balancer.instance_ids]}
        return ActionResult(result)

    def describe_load_balancer_attributes(self) -> ActionResult:
        load_balancer_name = self._get_param("LoadBalancerName")
        load_balancer = self.elb_backend.get_load_balancer(load_balancer_name)
        result = {"LoadBalancerAttributes": load_balancer.attributes}
        return ActionResult(result)

    def modify_load_balancer_attributes(self) -> ActionResult:
        load_balancer_name = self._get_param("LoadBalancerName")
        load_balancer = self.elb_backend.get_load_balancer(load_balancer_name)

        cross_zone = self._get_dict_param(
            "LoadBalancerAttributes.CrossZoneLoadBalancing."
        )
        if cross_zone:
            self.elb_backend.modify_load_balancer_attributes(
                load_balancer_name, cross_zone=cross_zone
            )

        access_log = self._get_dict_param("LoadBalancerAttributes.AccessLog.")
        if access_log:
            self.elb_backend.modify_load_balancer_attributes(
                load_balancer_name, access_log=access_log
            )

        connection_draining = self._get_dict_param(
            "LoadBalancerAttributes.ConnectionDraining."
        )
        if connection_draining:
            self.elb_backend.modify_load_balancer_attributes(
                load_balancer_name, connection_draining=connection_draining
            )

        connection_settings = self._get_dict_param(
            "LoadBalancerAttributes.ConnectionSettings."
        )
        if connection_settings:
            self.elb_backend.modify_load_balancer_attributes(
                load_balancer_name, connection_settings=connection_settings
            )

        additional_attributes_raw = self._get_multi_param(
            "LoadBalancerAttributes.AdditionalAttributes.member"
        )
        additional_attributes = []
        for attr in additional_attributes_raw:
            key = attr.get("Key")
            value = attr.get("Value")
            additional_attributes.append({"Key": key, "Value": value})

        if additional_attributes:
            self.elb_backend.modify_load_balancer_attributes(
                load_balancer_name, additional_attributes=additional_attributes
            )
        result = {
            "LoadBalancerName": load_balancer.name,
            "LoadBalancerAttributes": load_balancer.attributes,
        }
        return ActionResult(result)

    def create_load_balancer_policy(self) -> ActionResult:
        load_balancer_name = self._get_param("LoadBalancerName")

        policy_name = self._get_param("PolicyName")
        policy_type_name = self._get_param("PolicyTypeName")
        policy_attrs = self._get_multi_param("PolicyAttributes.member.")

        self.elb_backend.create_load_balancer_policy(
            load_balancer_name, policy_name, policy_type_name, policy_attrs
        )
        return EmptyResult()

    def create_app_cookie_stickiness_policy(self) -> ActionResult:
        load_balancer_name = self._get_param("LoadBalancerName")

        policy_name = self._get_param("PolicyName")
        cookie_name = self._get_param("CookieName")

        self.elb_backend.create_app_cookie_stickiness_policy(
            load_balancer_name, policy_name, cookie_name
        )
        return EmptyResult()

    def create_lb_cookie_stickiness_policy(self) -> ActionResult:
        load_balancer_name = self._get_param("LoadBalancerName")

        policy_name = self._get_param("PolicyName")
        cookie_expirations = self._get_param("CookieExpirationPeriod")
        if cookie_expirations:
            cookie_expiration_period = int(cookie_expirations)
        else:
            cookie_expiration_period = None

        self.elb_backend.create_lb_cookie_stickiness_policy(
            load_balancer_name, policy_name, cookie_expiration_period
        )
        return EmptyResult()

    def set_load_balancer_policies_of_listener(self) -> ActionResult:
        load_balancer_name = self._get_param("LoadBalancerName")
        load_balancer = self.elb_backend.get_load_balancer(load_balancer_name)
        load_balancer_port = int(self._get_param("LoadBalancerPort"))

        mb_listener = [
            listner
            for listner in load_balancer.listeners
            if int(listner.load_balancer_port) == load_balancer_port
        ]
        if mb_listener:
            policies = self._get_multi_param("PolicyNames.member")
            self.elb_backend.set_load_balancer_policies_of_listener(
                load_balancer_name, load_balancer_port, policies
            )
        # else: explode?
        return EmptyResult()

    def set_load_balancer_policies_for_backend_server(self) -> ActionResult:
        load_balancer_name = self.querystring.get("LoadBalancerName")[0]  # type: ignore
        load_balancer = self.elb_backend.get_load_balancer(load_balancer_name)
        instance_port = int(self.querystring.get("InstancePort")[0])  # type: ignore

        mb_backend = [
            b for b in load_balancer.backends if int(b.instance_port) == instance_port
        ]
        if mb_backend:
            policies = self._get_multi_param("PolicyNames.member")
            self.elb_backend.set_load_balancer_policies_for_backend_server(
                load_balancer_name, instance_port, policies
            )
        # else: explode?

        return EmptyResult()

    def describe_load_balancer_policies(self) -> ActionResult:
        load_balancer_name = self.querystring.get("LoadBalancerName")[0]  # type: ignore
        names = self._get_multi_param("PolicyNames.member.")
        policies = self.elb_backend.describe_load_balancer_policies(
            lb_name=load_balancer_name, policy_names=names
        )
        result = {"PolicyDescriptions": policies}
        return ActionResult(result)

    def describe_instance_health(self) -> ActionResult:
        lb_name = self._get_param("LoadBalancerName")
        instances = self._get_params().get("Instances", [])
        instances = self.elb_backend.describe_instance_health(lb_name, instances)
        result = {
            "InstanceStates": [
                {
                    "Description": "N/A",
                    "InstanceId": instance["InstanceId"],
                    "State": instance["State"],
                    "ReasonCode": "N/A",
                }
                for instance in instances
            ]
        }
        return ActionResult(result)

    def add_tags(self) -> ActionResult:
        for key, value in self.querystring.items():
            if "LoadBalancerNames.member" in key:
                load_balancer_name = value[0]
                elb = self.elb_backend.get_load_balancer(load_balancer_name)
                if not elb:
                    raise LoadBalancerNotFoundError(load_balancer_name)

                self._add_tags(elb)

        return EmptyResult()

    def remove_tags(self) -> ActionResult:
        for key in self.querystring:
            if "LoadBalancerNames.member" in key:
                number = key.split(".")[2]
                load_balancer_name = self._get_param(
                    f"LoadBalancerNames.member.{number}"
                )
                elb = self.elb_backend.get_load_balancer(load_balancer_name)
                if not elb:
                    raise LoadBalancerNotFoundError(load_balancer_name)

                for t_key, t_val in self.querystring.items():
                    if t_key.startswith("Tags.member."):
                        if t_key.split(".")[3] == "Key":
                            elb.remove_tag(t_val[0])

        return EmptyResult()

    def describe_tags(self) -> ActionResult:
        elbs = []
        for key in self.querystring:
            if "LoadBalancerNames.member" in key:
                number = key.split(".")[2]
                load_balancer_name = self._get_param(
                    f"LoadBalancerNames.member.{number}"
                )
                elb = self.elb_backend.get_load_balancer(load_balancer_name)
                if not elb:
                    raise LoadBalancerNotFoundError(load_balancer_name)
                elbs.append(elb)
        result = {
            "TagDescriptions": [
                {"LoadBalancerName": elb.name, "Tags": elb.tags} for elb in elbs
            ]
        }
        return ActionResult(result)

    def _add_tags(self, elb: LoadBalancer) -> None:
        tag_values = []
        tag_keys = []

        for t_key, t_val in sorted(self.querystring.items()):
            if t_key.startswith("Tags.member."):
                if t_key.split(".")[3] == "Key":
                    tag_keys.extend(t_val)
                elif t_key.split(".")[3] == "Value":
                    tag_values.extend(t_val)

        count_dict = {}
        for i in tag_keys:
            count_dict[i] = tag_keys.count(i)

        counts = sorted(count_dict.items(), key=lambda i: i[1], reverse=True)

        if counts and counts[0][1] > 1:
            # We have dupes...
            raise DuplicateTagKeysError(counts[0])

        for tag_key, tag_value in zip(tag_keys, tag_values):
            elb.add_tag(tag_key, tag_value)

    def enable_availability_zones_for_load_balancer(self) -> ActionResult:
        params = self._get_params()
        load_balancer_name = params.get("LoadBalancerName")
        availability_zones = params.get("AvailabilityZones")
        availability_zones = (
            self.elb_backend.enable_availability_zones_for_load_balancer(
                load_balancer_name=load_balancer_name,  # type: ignore[arg-type]
                availability_zones=availability_zones,  # type: ignore[arg-type]
            )
        )
        result = {"AvailabilityZones": availability_zones}
        return ActionResult(result)

    def disable_availability_zones_for_load_balancer(self) -> ActionResult:
        params = self._get_params()
        load_balancer_name = params.get("LoadBalancerName")
        availability_zones = params.get("AvailabilityZones")
        availability_zones = (
            self.elb_backend.disable_availability_zones_for_load_balancer(
                load_balancer_name=load_balancer_name,  # type: ignore[arg-type]
                availability_zones=availability_zones,  # type: ignore[arg-type]
            )
        )
        result = {"AvailabilityZones": availability_zones}
        return ActionResult(result)

    def attach_load_balancer_to_subnets(self) -> ActionResult:
        params = self._get_params()
        load_balancer_name = params.get("LoadBalancerName")
        subnets = params.get("Subnets")

        all_subnets = self.elb_backend.attach_load_balancer_to_subnets(
            load_balancer_name,  # type: ignore[arg-type]
            subnets,  # type: ignore[arg-type]
        )
        result = {"Subnets": all_subnets}
        return ActionResult(result)

    def detach_load_balancer_from_subnets(self) -> ActionResult:
        params = self._get_params()
        load_balancer_name = params.get("LoadBalancerName")
        subnets = params.get("Subnets")

        all_subnets = self.elb_backend.detach_load_balancer_from_subnets(
            load_balancer_name,  # type: ignore[arg-type]
            subnets,  # type: ignore[arg-type]
        )
        result = {"Subnets": all_subnets}
        return ActionResult(result)
