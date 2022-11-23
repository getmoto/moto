import datetime
import pytz
from collections import OrderedDict
from typing import List, Iterable

from moto.core import BaseBackend, BackendDict, BaseModel, CloudFormationModel
from moto.ec2.models import ec2_backends
from moto.ec2.exceptions import InvalidInstanceIdError
from moto.moto_api._internal import mock_random
from .exceptions import (
    BadHealthCheckDefinition,
    DuplicateLoadBalancerName,
    DuplicateListenerError,
    EmptyListenersError,
    InvalidSecurityGroupError,
    LoadBalancerNotFoundError,
    NoActiveLoadBalancerFoundError,
    PolicyNotFoundError,
    TooManyTagsError,
    CertificateNotFoundException,
)
from .policies import AppCookieStickinessPolicy, LbCookieStickinessPolicy, OtherPolicy


class FakeHealthCheck(BaseModel):
    def __init__(
        self, timeout, healthy_threshold, unhealthy_threshold, interval, target
    ):
        self.timeout = timeout
        self.healthy_threshold = healthy_threshold
        self.unhealthy_threshold = unhealthy_threshold
        self.interval = interval
        self.target = target
        if not target.startswith(("HTTP", "TCP", "HTTPS", "SSL")):
            raise BadHealthCheckDefinition


class FakeListener(BaseModel):
    def __init__(self, load_balancer_port, instance_port, protocol, ssl_certificate_id):
        self.load_balancer_port = load_balancer_port
        self.instance_port = instance_port
        self.protocol = protocol.upper()
        self.ssl_certificate_id = ssl_certificate_id
        self.policy_names = []

    def __repr__(self):
        return f"FakeListener(lbp: {self.load_balancer_port}, inp: {self.instance_port}, pro: {self.protocol}, cid: {self.ssl_certificate_id}, policies: {self.policy_names})"


class FakeBackend(BaseModel):
    def __init__(self, instance_port):
        self.instance_port = instance_port
        self.policy_names = []

    def __repr__(self):
        return f"FakeBackend(inp: {self.instance_port}, policies: {self.policy_names})"


class FakeLoadBalancer(CloudFormationModel):
    def __init__(
        self,
        name,
        zones,
        ports,
        scheme=None,
        vpc_id=None,
        subnets=None,
        security_groups=None,
        elb_backend=None,
    ):
        self.name = name
        self.health_check = None
        self.instance_sparse_ids = []
        self.instance_autoscaling_ids = []
        self.zones = zones
        self.listeners = []
        self.backends = []
        self.created_time = datetime.datetime.now(pytz.utc)
        self.scheme = scheme or "internet-facing"
        self.attributes = FakeLoadBalancer.get_default_attributes()
        self.policies = []
        self.security_groups = security_groups or []
        self.subnets = subnets or []
        self.vpc_id = vpc_id
        self.tags = {}
        self.dns_name = f"{name}.us-east-1.elb.amazonaws.com"

        for port in ports:
            listener = FakeListener(
                protocol=(port.get("protocol") or port["Protocol"]),
                load_balancer_port=(
                    port.get("load_balancer_port") or port["LoadBalancerPort"]
                ),
                instance_port=(port.get("instance_port") or port["InstancePort"]),
                ssl_certificate_id=port.get(
                    "ssl_certificate_id", port.get("SSLCertificateId")
                ),
            )
            if (
                listener.ssl_certificate_id
                and not listener.ssl_certificate_id.startswith("arn:aws:iam:")
            ):
                elb_backend._register_certificate(
                    listener.ssl_certificate_id, self.dns_name
                )

            self.listeners.append(listener)

            # it is unclear per the AWS documentation as to when or how backend
            # information gets set, so let's guess and set it here *shrug*
            backend = FakeBackend(
                instance_port=(port.get("instance_port") or port["InstancePort"])
            )
            self.backends.append(backend)

    @property
    def instance_ids(self):
        """Return all the instances attached to the ELB"""
        return self.instance_sparse_ids + self.instance_autoscaling_ids

    @staticmethod
    def cloudformation_name_type():
        return "LoadBalancerName"

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-elasticloadbalancing-loadbalancer.html
        return "AWS::ElasticLoadBalancing::LoadBalancer"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, account_id, region_name, **kwargs
    ):
        properties = cloudformation_json["Properties"]

        elb_backend = elb_backends[account_id][region_name]
        new_elb = elb_backend.create_load_balancer(
            name=properties.get("LoadBalancerName", resource_name),
            zones=properties.get("AvailabilityZones", []),
            ports=properties["Listeners"],
            scheme=properties.get("Scheme", "internet-facing"),
        )

        instance_ids = properties.get("Instances", [])
        for instance_id in instance_ids:
            elb_backend.register_instances(new_elb.name, [instance_id])

        policies = properties.get("Policies", [])
        port_policies = {}
        for policy in policies:
            policy_name = policy["PolicyName"]
            other_policy = OtherPolicy()
            other_policy.policy_name = policy_name
            elb_backend.create_lb_other_policy(new_elb.name, other_policy)
            for port in policy.get("InstancePorts", []):
                policies_for_port = port_policies.get(port, set())
                policies_for_port.add(policy_name)
                port_policies[port] = policies_for_port

        for port, policies in port_policies.items():
            elb_backend.set_load_balancer_policies_of_backend_server(
                new_elb.name, port, list(policies)
            )

        health_check = properties.get("HealthCheck")
        if health_check:
            elb_backend.configure_health_check(
                load_balancer_name=new_elb.name,
                timeout=health_check["Timeout"],
                healthy_threshold=health_check["HealthyThreshold"],
                unhealthy_threshold=health_check["UnhealthyThreshold"],
                interval=health_check["Interval"],
                target=health_check["Target"],
            )

        return new_elb

    @classmethod
    def update_from_cloudformation_json(
        cls,
        original_resource,
        new_resource_name,
        cloudformation_json,
        account_id,
        region_name,
    ):
        cls.delete_from_cloudformation_json(
            original_resource.name, cloudformation_json, account_id, region_name
        )
        return cls.create_from_cloudformation_json(
            new_resource_name, cloudformation_json, account_id, region_name
        )

    @classmethod
    def delete_from_cloudformation_json(
        cls, resource_name, cloudformation_json, account_id, region_name
    ):
        elb_backend = elb_backends[account_id][region_name]
        try:
            elb_backend.delete_load_balancer(resource_name)
        except KeyError:
            pass

    @property
    def physical_resource_id(self):
        return self.name

    @classmethod
    def has_cfn_attr(cls, attr):
        return attr in [
            "CanonicalHostedZoneName",
            "CanonicalHostedZoneNameID",
            "DNSName",
            "SourceSecurityGroup.GroupName",
            "SourceSecurityGroup.OwnerAlias",
        ]

    def get_cfn_attribute(self, attribute_name):
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException

        if attribute_name == "CanonicalHostedZoneName":
            raise NotImplementedError(
                '"Fn::GetAtt" : [ "{0}" , "CanonicalHostedZoneName" ]"'
            )
        elif attribute_name == "CanonicalHostedZoneNameID":
            raise NotImplementedError(
                '"Fn::GetAtt" : [ "{0}" , "CanonicalHostedZoneNameID" ]"'
            )
        elif attribute_name == "DNSName":
            return self.dns_name
        elif attribute_name == "SourceSecurityGroup.GroupName":
            raise NotImplementedError(
                '"Fn::GetAtt" : [ "{0}" , "SourceSecurityGroup.GroupName" ]"'
            )
        elif attribute_name == "SourceSecurityGroup.OwnerAlias":
            raise NotImplementedError(
                '"Fn::GetAtt" : [ "{0}" , "SourceSecurityGroup.OwnerAlias" ]"'
            )
        raise UnformattedGetAttTemplateException()

    @classmethod
    def get_default_attributes(cls):
        attributes = dict()
        attributes["cross_zone_load_balancing"] = {"enabled": False}
        attributes["connection_draining"] = {"enabled": False}
        attributes["access_log"] = {"enabled": False}
        attributes["connection_settings"] = {"idle_timeout": 60}

        return attributes

    def add_tag(self, key, value):
        if len(self.tags) >= 10 and key not in self.tags:
            raise TooManyTagsError()
        self.tags[key] = value

    def list_tags(self):
        return self.tags

    def remove_tag(self, key):
        if key in self.tags:
            del self.tags[key]

    def delete(self, account_id, region):
        """Not exposed as part of the ELB API - used for CloudFormation."""
        elb_backends[account_id][region].delete_load_balancer(self.name)


class ELBBackend(BaseBackend):
    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
        self.load_balancers = OrderedDict()

    def create_load_balancer(
        self,
        name,
        zones,
        ports,
        scheme="internet-facing",
        subnets=None,
        security_groups=None,
    ):
        vpc_id = None
        ec2_backend = ec2_backends[self.account_id][self.region_name]
        if subnets:
            subnet = ec2_backend.get_subnet(subnets[0])
            vpc_id = subnet.vpc_id
        elif zones:
            subnets = [
                ec2_backend.get_default_subnet(availability_zone=zone).id
                for zone in zones
            ]
            subnet = ec2_backend.get_subnet(subnets[0])
            vpc_id = subnet.vpc_id
        if name in self.load_balancers:
            raise DuplicateLoadBalancerName(name)
        if not ports:
            raise EmptyListenersError()
        if not security_groups:
            sg = ec2_backend.create_security_group(
                name=f"default_elb_{mock_random.uuid4()}",
                description="ELB created security group used when no security group is specified during ELB creation - modifications could impact traffic to future ELBs",
                vpc_id=vpc_id,
            )
            security_groups = [sg.id]
        for security_group in security_groups:
            if ec2_backend.get_security_group_from_id(security_group) is None:
                raise InvalidSecurityGroupError()
        new_load_balancer = FakeLoadBalancer(
            name=name,
            zones=zones,
            ports=ports,
            scheme=scheme,
            subnets=subnets,
            security_groups=security_groups,
            vpc_id=vpc_id,
            elb_backend=self,
        )
        self.load_balancers[name] = new_load_balancer
        return new_load_balancer

    def create_load_balancer_listeners(self, name, ports):
        balancer = self.load_balancers.get(name, None)
        if balancer:
            for port in ports:
                protocol = port["protocol"]
                instance_port = port["instance_port"]
                lb_port = port["load_balancer_port"]
                ssl_certificate_id = port.get("ssl_certificate_id")
                for listener in balancer.listeners:
                    if lb_port == listener.load_balancer_port:
                        if protocol.lower() != listener.protocol.lower():
                            raise DuplicateListenerError(name, lb_port)
                        if instance_port != listener.instance_port:
                            raise DuplicateListenerError(name, lb_port)
                        if ssl_certificate_id != listener.ssl_certificate_id:
                            raise DuplicateListenerError(name, lb_port)
                        break
                else:
                    if ssl_certificate_id and not ssl_certificate_id.startswith(
                        "arn:aws:iam::"
                    ):
                        self._register_certificate(
                            ssl_certificate_id, balancer.dns_name
                        )
                    balancer.listeners.append(
                        FakeListener(
                            lb_port, instance_port, protocol, ssl_certificate_id
                        )
                    )

        return balancer

    def describe_load_balancers(self, names: List[str]) -> List[FakeLoadBalancer]:
        balancers = self.load_balancers.values()
        if names:
            matched_balancers = [
                balancer for balancer in balancers if balancer.name in names
            ]
            if len(names) != len(matched_balancers):
                missing_elb = list(set(names) - set(matched_balancers))[0]
                raise LoadBalancerNotFoundError(missing_elb)
            return matched_balancers
        else:
            return balancers

    def describe_load_balancer_policies(self, lb_name, policy_names):
        lb = self.describe_load_balancers([lb_name])[0]
        policies = lb.policies
        if policy_names:
            policies = [p for p in policies if p.policy_name in policy_names]
            if len(policy_names) != len(policies):
                raise PolicyNotFoundError()
        return policies

    def describe_instance_health(self, lb_name, instances):
        elb = self.get_load_balancer(lb_name)
        if elb is None:
            raise NoActiveLoadBalancerFoundError(name=lb_name)
        provided_ids = [i["InstanceId"] for i in instances]
        registered_ids = elb.instance_ids
        ec2_backend = ec2_backends[self.account_id][self.region_name]
        if len(provided_ids) == 0:
            provided_ids = registered_ids
        instances = []
        for instance_id in provided_ids:
            if instance_id not in registered_ids:
                instances.append({"InstanceId": instance_id, "State": "Unknown"})
            else:
                try:
                    instance = ec2_backend.get_instance(instance_id)
                    state = "InService" if instance.is_running() else "OutOfService"
                    instances.append({"InstanceId": instance_id, "State": state})
                except InvalidInstanceIdError:
                    pass

        return instances

    def delete_load_balancer_listeners(self, name, ports):
        balancer = self.load_balancers.get(name, None)
        listeners = []
        if balancer:
            for lb_port in ports:
                for listener in balancer.listeners:
                    if int(lb_port) == int(listener.load_balancer_port):
                        continue
                    else:
                        listeners.append(listener)
        balancer.listeners = listeners
        return balancer

    def delete_load_balancer(self, load_balancer_name):
        self.load_balancers.pop(load_balancer_name, None)

    def delete_load_balancer_policy(self, lb_name, policy_name):
        lb = self.get_load_balancer(lb_name)
        lb.policies = [p for p in lb.policies if p.policy_name != policy_name]

    def get_load_balancer(self, load_balancer_name):
        return self.load_balancers.get(load_balancer_name)

    def apply_security_groups_to_load_balancer(
        self, load_balancer_name, security_group_ids
    ):
        load_balancer = self.load_balancers.get(load_balancer_name)
        ec2_backend = ec2_backends[self.account_id][self.region_name]
        for security_group_id in security_group_ids:
            if ec2_backend.get_security_group_from_id(security_group_id) is None:
                raise InvalidSecurityGroupError()
        load_balancer.security_groups = security_group_ids

    def configure_health_check(
        self,
        load_balancer_name,
        timeout,
        healthy_threshold,
        unhealthy_threshold,
        interval,
        target,
    ):
        check = FakeHealthCheck(
            timeout, healthy_threshold, unhealthy_threshold, interval, target
        )
        load_balancer = self.get_load_balancer(load_balancer_name)
        load_balancer.health_check = check
        return check

    def set_load_balancer_listener_ssl_certificate(
        self, name, lb_port, ssl_certificate_id
    ):
        balancer = self.load_balancers.get(name, None)
        if balancer:
            for idx, listener in enumerate(balancer.listeners):
                if lb_port == listener.load_balancer_port:
                    balancer.listeners[idx].ssl_certificate_id = ssl_certificate_id
                    if ssl_certificate_id:
                        self._register_certificate(
                            ssl_certificate_id, balancer.dns_name
                        )
        return balancer

    def register_instances(
        self,
        load_balancer_name: str,
        instance_ids: Iterable[str],
        from_autoscaling: bool = False,
    ) -> FakeLoadBalancer:
        load_balancer = self.get_load_balancer(load_balancer_name)
        attr_name = (
            "instance_sparse_ids"
            if not from_autoscaling
            else "instance_autoscaling_ids"
        )

        actual_instance_ids = getattr(load_balancer, attr_name)
        actual_instance_ids.extend(instance_ids)
        return load_balancer

    def deregister_instances(
        self,
        load_balancer_name: str,
        instance_ids: Iterable[str],
        from_autoscaling: bool = False,
    ) -> FakeLoadBalancer:
        load_balancer = self.get_load_balancer(load_balancer_name)
        attr_name = (
            "instance_sparse_ids"
            if not from_autoscaling
            else "instance_autoscaling_ids"
        )
        actual_instance_ids = getattr(load_balancer, attr_name)

        new_instance_ids = [
            instance_id
            for instance_id in actual_instance_ids
            if instance_id not in instance_ids
        ]

        setattr(load_balancer, attr_name, new_instance_ids)

        return load_balancer

    def modify_load_balancer_attributes(
        self,
        load_balancer_name,
        cross_zone=None,
        connection_settings=None,
        connection_draining=None,
        access_log=None,
    ):
        load_balancer = self.get_load_balancer(load_balancer_name)
        if cross_zone:
            load_balancer.attributes["cross_zone_load_balancing"] = cross_zone
        if connection_settings:
            load_balancer.attributes["connection_settings"] = connection_settings
        if connection_draining:
            load_balancer.attributes["connection_draining"] = connection_draining
            if "timeout" not in connection_draining:
                load_balancer.attributes["connection_draining"][
                    "timeout"
                ] = 300  # default
        if access_log:
            load_balancer.attributes["access_log"] = access_log

    def create_lb_other_policy(
        self, load_balancer_name, policy_name, policy_type_name, policy_attrs
    ):
        load_balancer = self.get_load_balancer(load_balancer_name)
        if policy_name not in [p.policy_name for p in load_balancer.policies]:
            load_balancer.policies.append(
                OtherPolicy(policy_name, policy_type_name, policy_attrs)
            )

        return load_balancer

    def create_app_cookie_stickiness_policy(
        self, load_balancer_name, policy_name, cookie_name
    ):
        load_balancer = self.get_load_balancer(load_balancer_name)
        policy = AppCookieStickinessPolicy(policy_name, cookie_name)
        load_balancer.policies.append(policy)
        return load_balancer

    def create_lb_cookie_stickiness_policy(
        self, load_balancer_name, policy_name, cookie_expiration_period
    ):
        load_balancer = self.get_load_balancer(load_balancer_name)
        policy = LbCookieStickinessPolicy(policy_name, cookie_expiration_period)
        load_balancer.policies.append(policy)
        return load_balancer

    def set_load_balancer_policies_of_backend_server(
        self, load_balancer_name, instance_port, policies
    ):
        load_balancer = self.get_load_balancer(load_balancer_name)
        backend = [
            b for b in load_balancer.backends if int(b.instance_port) == instance_port
        ][0]
        backend_idx = load_balancer.backends.index(backend)
        backend.policy_names = policies
        load_balancer.backends[backend_idx] = backend
        return load_balancer

    def set_load_balancer_policies_of_listener(
        self, load_balancer_name, load_balancer_port, policies
    ):
        load_balancer = self.get_load_balancer(load_balancer_name)
        listener = [
            l_listener
            for l_listener in load_balancer.listeners
            if int(l_listener.load_balancer_port) == load_balancer_port
        ][0]
        listener_idx = load_balancer.listeners.index(listener)
        listener.policy_names = policies
        load_balancer.listeners[listener_idx] = listener
        return load_balancer

    def _register_certificate(self, ssl_certificate_id, dns_name):
        from moto.acm.models import acm_backends, CertificateNotFound

        acm_backend = acm_backends[self.account_id][self.region_name]
        try:
            acm_backend.set_certificate_in_use_by(ssl_certificate_id, dns_name)
        except CertificateNotFound:
            raise CertificateNotFoundException()

    def enable_availability_zones_for_load_balancer(
        self, load_balancer_name, availability_zones
    ):
        load_balancer = self.get_load_balancer(load_balancer_name)
        load_balancer.zones = sorted(
            list(set(load_balancer.zones + availability_zones))
        )
        return load_balancer.zones

    def disable_availability_zones_for_load_balancer(
        self, load_balancer_name, availability_zones
    ):
        load_balancer = self.get_load_balancer(load_balancer_name)
        load_balancer.zones = sorted(
            list(
                set([az for az in load_balancer.zones if az not in availability_zones])
            )
        )
        return load_balancer.zones

    def attach_load_balancer_to_subnets(self, load_balancer_name, subnets):
        load_balancer = self.get_load_balancer(load_balancer_name)
        load_balancer.subnets = list(set(load_balancer.subnets + subnets))
        return load_balancer.subnets

    def detach_load_balancer_from_subnets(self, load_balancer_name, subnets):
        load_balancer = self.get_load_balancer(load_balancer_name)
        load_balancer.subnets = [s for s in load_balancer.subnets if s not in subnets]
        return load_balancer.subnets


# Use the same regions as EC2
elb_backends = BackendDict(ELBBackend, "ec2")
