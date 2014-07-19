from moto.core import BaseBackend


class FakeHealthCheck(object):
    def __init__(self, timeout, healthy_threshold, unhealthy_threshold,
                 interval, target):
        self.timeout = timeout
        self.healthy_threshold = healthy_threshold
        self.unhealthy_threshold = unhealthy_threshold
        self.interval = interval
        self.target = target


class FakeListener(object):
    def __init__(self, load_balancer_port, instance_port, protocol, ssl_certificate_id):
        self.load_balancer_port = load_balancer_port
        self.instance_port = instance_port
        self.protocol = protocol.upper()
        self.ssl_certificate_id = ssl_certificate_id


class FakeLoadBalancer(object):
    def __init__(self, name, zones, ports):
        self.name = name
        self.health_check = None
        self.instance_ids = []
        self.zones = zones
        self.listeners = []

        for protocol, lb_port, instance_port, ssl_certificate_id in ports:
            listener = FakeListener(
                protocol=protocol,
                load_balancer_port=lb_port,
                instance_port=instance_port,
                ssl_certificate_id=ssl_certificate_id
            )
            self.listeners.append(listener)

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json):
        properties = cloudformation_json['Properties']

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


class ELBBackend(BaseBackend):

    def __init__(self):
        self.load_balancers = {}

    def create_load_balancer(self, name, zones, ports):
        new_load_balancer = FakeLoadBalancer(name=name, zones=zones, ports=ports)
        self.load_balancers[name] = new_load_balancer
        return new_load_balancer

    def create_load_balancer_listeners(self, name, ports):
        balancer = self.load_balancers.get(name, None)
        if balancer:
            for protocol, lb_port, instance_port, ssl_certificate_id in ports:
                for listener in balancer.listeners:
                    if lb_port == listener.load_balancer_port:
                        break
                else:
                    balancer.listeners.append(FakeListener(lb_port, instance_port, protocol, ssl_certificate_id))

        return balancer

    def describe_load_balancers(self, names):
        balancers = self.load_balancers.values()
        if names:
            return [balancer for balancer in balancers if balancer.name in names]
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

elb_backend = ELBBackend()
