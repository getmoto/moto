from __future__ import unicode_literals

import boto.ec2.elb
from boto.ec2.elb.attributes import (
    LbAttributes,
    ConnectionSettingAttribute,
    ConnectionDrainingAttribute,
    AccessLogAttribute,
    CrossZoneLoadBalancingAttribute,
)
from boto.ec2.elb.policies import Policies
from moto.core import BaseBackend
from .exceptions import LoadBalancerNotFoundError, TooManyTagsError, BadHealthCheckDefinition


class FakeHealthCheck(object):
    def __init__(self, timeout, healthy_threshold, unhealthy_threshold,
                 interval, target):
        self.timeout = timeout
        self.healthy_threshold = healthy_threshold
        self.unhealthy_threshold = unhealthy_threshold
        self.interval = interval
        self.target = target
        if not target.startswith(('HTTP', 'TCP', 'HTTPS', 'SSL')):
            raise BadHealthCheckDefinition


class FakeListener(object):
    def __init__(self, load_balancer_port, instance_port, protocol, ssl_certificate_id):
        self.load_balancer_port = load_balancer_port
        self.instance_port = instance_port
        self.protocol = protocol.upper()
        self.ssl_certificate_id = ssl_certificate_id
        self.policy_names = []

    def __repr__(self):
        return "FakeListener(lbp: %s, inp: %s, pro: %s, cid: %s, policies: %s)" % (self.load_balancer_port, self.instance_port, self.protocol, self.ssl_certificate_id, self.policy_names)


class FakeBackend(object):
    def __init__(self, instance_port):
        self.instance_port = instance_port
        self.policy_names = []

    def __repr__(self):
        return "FakeBackend(inp: %s, policies: %s)" % (self.instance_port, self.policy_names)


class FakeLoadBalancer(object):
    def __init__(self, name, zones, ports, scheme='internet-facing',):
        self.name = name
        self.health_check = None
        self.instance_ids = []
        self.zones = zones
        self.listeners = []
        self.backends = []
        self.scheme = scheme
        self.attributes = FakeLoadBalancer.get_default_attributes()
        self.policies = Policies()
        self.policies.other_policies = []
        self.policies.app_cookie_stickiness_policies = []
        self.policies.lb_cookie_stickiness_policies = []
        self.tags = {}

        for port in ports:
            listener = FakeListener(
                protocol=port['protocol'],
                load_balancer_port=port['load_balancer_port'],
                instance_port=port['instance_port'],
                ssl_certificate_id=port.get('sslcertificate_id'),
            )
            self.listeners.append(listener)

            # it is unclear per the AWS documentation as to when or how backend
            # information gets set, so let's guess and set it here *shrug*
            backend = FakeBackend(
                instance_port=port['instance_port'],
            )
            self.backends.append(backend)

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json, region_name):
        properties = cloudformation_json['Properties']

        elb_backend = elb_backends[region_name]
        new_elb = elb_backend.create_load_balancer(
            name=properties.get('LoadBalancerName', resource_name),
            zones=properties.get('AvailabilityZones'),
            ports=[],
        )

        instance_ids = cloudformation_json.get('Instances', [])
        for instance_id in instance_ids:
            elb_backend.register_instances(new_elb.name, [instance_id])
        return new_elb

    @property
    def physical_resource_id(self):
        return self.name

    def get_cfn_attribute(self, attribute_name):
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException
        if attribute_name == 'CanonicalHostedZoneName':
            raise NotImplementedError('"Fn::GetAtt" : [ "{0}" , "CanonicalHostedZoneName" ]"')
        elif attribute_name == 'CanonicalHostedZoneNameID':
            raise NotImplementedError('"Fn::GetAtt" : [ "{0}" , "CanonicalHostedZoneNameID" ]"')
        elif attribute_name == 'DNSName':
            raise NotImplementedError('"Fn::GetAtt" : [ "{0}" , "DNSName" ]"')
        elif attribute_name == 'SourceSecurityGroup.GroupName':
            raise NotImplementedError('"Fn::GetAtt" : [ "{0}" , "SourceSecurityGroup.GroupName" ]"')
        elif attribute_name == 'SourceSecurityGroup.OwnerAlias':
            raise NotImplementedError('"Fn::GetAtt" : [ "{0}" , "SourceSecurityGroup.OwnerAlias" ]"')
        raise UnformattedGetAttTemplateException()

    @classmethod
    def get_default_attributes(cls):
        attributes = LbAttributes()

        cross_zone_load_balancing = CrossZoneLoadBalancingAttribute()
        cross_zone_load_balancing.enabled = False
        attributes.cross_zone_load_balancing = cross_zone_load_balancing

        connection_draining = ConnectionDrainingAttribute()
        connection_draining.enabled = False
        attributes.connection_draining = connection_draining

        access_log = AccessLogAttribute()
        access_log.enabled = False
        attributes.access_log = access_log

        connection_settings = ConnectionSettingAttribute()
        connection_settings.idle_timeout = 60
        attributes.connecting_settings = connection_settings

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


class ELBBackend(BaseBackend):

    def __init__(self):
        self.load_balancers = {}

    def create_load_balancer(self, name, zones, ports, scheme='internet-facing'):
        new_load_balancer = FakeLoadBalancer(name=name, zones=zones, ports=ports, scheme=scheme)
        self.load_balancers[name] = new_load_balancer
        return new_load_balancer

    def create_load_balancer_listeners(self, name, ports):
        balancer = self.load_balancers.get(name, None)
        if balancer:
            for port in ports:
                protocol = port['protocol']
                instance_port = port['instance_port']
                lb_port = port['load_balancer_port']
                ssl_certificate_id = port.get('sslcertificate_id')
                for listener in balancer.listeners:
                    if lb_port == listener.load_balancer_port:
                        break
                else:
                    balancer.listeners.append(FakeListener(lb_port, instance_port, protocol, ssl_certificate_id))

        return balancer

    def describe_load_balancers(self, names):
        balancers = self.load_balancers.values()
        if names:
            matched_balancers = [balancer for balancer in balancers if balancer.name in names]
            if len(names) != len(matched_balancers):
                missing_elb = list(set(names) - set(matched_balancers))[0]
                raise LoadBalancerNotFoundError(missing_elb)
            return matched_balancers
        else:
            return balancers

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

    def get_load_balancer(self, load_balancer_name):
        return self.load_balancers.get(load_balancer_name)

    def configure_health_check(self, load_balancer_name, timeout,
                               healthy_threshold, unhealthy_threshold, interval,
                               target):
        check = FakeHealthCheck(timeout, healthy_threshold, unhealthy_threshold,
                                interval, target)
        load_balancer = self.get_load_balancer(load_balancer_name)
        load_balancer.health_check = check
        return check

    def set_load_balancer_listener_sslcertificate(self, name, lb_port, ssl_certificate_id):
        balancer = self.load_balancers.get(name, None)
        if balancer:
            for idx, listener in enumerate(balancer.listeners):
                if lb_port == listener.load_balancer_port:
                    balancer.listeners[idx].ssl_certificate_id = ssl_certificate_id

        return balancer

    def register_instances(self, load_balancer_name, instance_ids):
        load_balancer = self.get_load_balancer(load_balancer_name)
        load_balancer.instance_ids.extend(instance_ids)
        return load_balancer

    def deregister_instances(self, load_balancer_name, instance_ids):
        load_balancer = self.get_load_balancer(load_balancer_name)
        new_instance_ids = [instance_id for instance_id in load_balancer.instance_ids if instance_id not in instance_ids]
        load_balancer.instance_ids = new_instance_ids
        return load_balancer

    def set_cross_zone_load_balancing_attribute(self, load_balancer_name, attribute):
        load_balancer = self.get_load_balancer(load_balancer_name)
        load_balancer.attributes.cross_zone_load_balancing = attribute
        return load_balancer

    def set_access_log_attribute(self, load_balancer_name, attribute):
        load_balancer = self.get_load_balancer(load_balancer_name)
        load_balancer.attributes.access_log = attribute
        return load_balancer

    def set_connection_draining_attribute(self, load_balancer_name, attribute):
        load_balancer = self.get_load_balancer(load_balancer_name)
        load_balancer.attributes.connection_draining = attribute
        return load_balancer

    def set_connection_settings_attribute(self, load_balancer_name, attribute):
        load_balancer = self.get_load_balancer(load_balancer_name)
        load_balancer.attributes.connecting_settings = attribute
        return load_balancer

    def create_lb_other_policy(self, load_balancer_name, other_policy):
        load_balancer = self.get_load_balancer(load_balancer_name)
        load_balancer.policies.other_policies.append(other_policy)
        return load_balancer

    def create_app_cookie_stickiness_policy(self, load_balancer_name, policy):
        load_balancer = self.get_load_balancer(load_balancer_name)
        load_balancer.policies.app_cookie_stickiness_policies.append(policy)
        return load_balancer

    def create_lb_cookie_stickiness_policy(self, load_balancer_name, policy):
        load_balancer = self.get_load_balancer(load_balancer_name)
        load_balancer.policies.lb_cookie_stickiness_policies.append(policy)
        return load_balancer

    def set_load_balancer_policies_of_backend_server(self, load_balancer_name, instance_port, policies):
        load_balancer = self.get_load_balancer(load_balancer_name)
        backend = [b for b in load_balancer.backends if int(b.instance_port) == instance_port][0]
        backend_idx = load_balancer.backends.index(backend)
        backend.policy_names = policies
        load_balancer.backends[backend_idx] = backend
        return load_balancer

    def set_load_balancer_policies_of_listener(self, load_balancer_name, load_balancer_port, policies):
        load_balancer = self.get_load_balancer(load_balancer_name)
        listener = [l for l in load_balancer.listeners if int(l.load_balancer_port) == load_balancer_port][0]
        listener_idx = load_balancer.listeners.index(listener)
        listener.policy_names = policies
        load_balancer.listeners[listener_idx] = listener
        return load_balancer


elb_backends = {}
for region in boto.ec2.elb.regions():
    elb_backends[region.name] = ELBBackend()
