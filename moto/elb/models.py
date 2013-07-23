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
    def __init__(self, load_balancer_port, instance_port, protocol):
        self.load_balancer_port = load_balancer_port
        self.instance_port = instance_port
        self.protocol = protocol.upper()


class FakeLoadBalancer(object):
    def __init__(self, name, zones, ports):
        self.name = name
        self.health_check = None
        self.instance_ids = []
        self.zones = zones
        self.listeners = []
        for protocol, lb_port, instance_port in ports:
            listener = FakeListener(
                protocol=protocol,
                load_balancer_port=lb_port,
                instance_port=instance_port,
            )
            self.listeners.append(listener)


class ELBBackend(BaseBackend):

    def __init__(self):
        self.load_balancers = {}

    def create_load_balancer(self, name, zones, ports):
        new_load_balancer = FakeLoadBalancer(name=name, zones=zones, ports=ports)
        self.load_balancers[name] = new_load_balancer
        return new_load_balancer

    def describe_load_balancers(self, names):
        balancers = self.load_balancers.values()
        if names:
            return [balancer for balancer in balancers if balancer.name in names]
        else:
            return balancers

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
