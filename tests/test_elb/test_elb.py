import boto
from boto.ec2.elb import HealthCheck
import sure  # noqa

from moto import mock_elb, mock_ec2


@mock_elb
def test_create_load_balancer():
    conn = boto.connect_elb()

    zones = ['us-east-1a', 'us-east-1b']
    ports = [(80, 8080, 'http'), (443, 8443, 'tcp')]
    conn.create_load_balancer('my-lb', zones, ports)

    balancers = conn.get_all_load_balancers()
    balancer = balancers[0]
    balancer.name.should.equal("my-lb")
    set(balancer.availability_zones).should.equal(set(['us-east-1a', 'us-east-1b']))
    listener1 = balancer.listeners[0]
    listener1.load_balancer_port.should.equal(80)
    listener1.instance_port.should.equal(8080)
    listener1.protocol.should.equal("HTTP")
    listener2 = balancer.listeners[1]
    listener2.load_balancer_port.should.equal(443)
    listener2.instance_port.should.equal(8443)
    listener2.protocol.should.equal("TCP")


@mock_elb
def test_get_load_balancers_by_name():
    conn = boto.connect_elb()

    zones = ['us-east-1a', 'us-east-1b']
    ports = [(80, 8080, 'http'), (443, 8443, 'tcp')]
    conn.create_load_balancer('my-lb1', zones, ports)
    conn.create_load_balancer('my-lb2', zones, ports)
    conn.create_load_balancer('my-lb3', zones, ports)

    conn.get_all_load_balancers().should.have.length_of(3)
    conn.get_all_load_balancers(load_balancer_names=['my-lb1']).should.have.length_of(1)
    conn.get_all_load_balancers(load_balancer_names=['my-lb1', 'my-lb2']).should.have.length_of(2)


@mock_elb
def test_delete_load_balancer():
    conn = boto.connect_elb()

    zones = ['us-east-1a']
    ports = [(80, 8080, 'http'), (443, 8443, 'tcp')]
    conn.create_load_balancer('my-lb', zones, ports)

    balancers = conn.get_all_load_balancers()
    balancers.should.have.length_of(1)

    conn.delete_load_balancer("my-lb")
    balancers = conn.get_all_load_balancers()
    balancers.should.have.length_of(0)


@mock_elb
def test_create_health_check():
    conn = boto.connect_elb()

    hc = HealthCheck(
        interval=20,
        healthy_threshold=3,
        unhealthy_threshold=5,
        target='HTTP:8080/health',
        timeout=23,
    )

    lb = conn.create_load_balancer('my-lb', [], [])
    lb.configure_health_check(hc)

    balancer = conn.get_all_load_balancers()[0]
    health_check = balancer.health_check
    health_check.interval.should.equal(20)
    health_check.healthy_threshold.should.equal(3)
    health_check.unhealthy_threshold.should.equal(5)
    health_check.target.should.equal('HTTP:8080/health')
    health_check.timeout.should.equal(23)


@mock_ec2
@mock_elb
def test_register_instances():
    ec2_conn = boto.connect_ec2()
    reservation = ec2_conn.run_instances('ami-1234abcd', 2)
    instance_id1 = reservation.instances[0].id
    instance_id2 = reservation.instances[1].id

    conn = boto.connect_elb()
    lb = conn.create_load_balancer('my-lb', [], [])

    lb.register_instances([instance_id1, instance_id2])

    balancer = conn.get_all_load_balancers()[0]
    instance_ids = [instance.id for instance in balancer.instances]
    set(instance_ids).should.equal(set([instance_id1, instance_id2]))


@mock_ec2
@mock_elb
def test_deregister_instances():
    ec2_conn = boto.connect_ec2()
    reservation = ec2_conn.run_instances('ami-1234abcd', 2)
    instance_id1 = reservation.instances[0].id
    instance_id2 = reservation.instances[1].id

    conn = boto.connect_elb()
    lb = conn.create_load_balancer('my-lb', [], [])

    lb.register_instances([instance_id1, instance_id2])

    balancer = conn.get_all_load_balancers()[0]
    balancer.instances.should.have.length_of(2)
    balancer.deregister_instances([instance_id1])

    balancer.instances.should.have.length_of(1)
    balancer.instances[0].id.should.equal(instance_id2)
